"""SQLite persistence for video metadata, frames, and embeddings.

This is the only module in AmonHen that contains SQL.

The vector column's dimension is baked into the table at creation time,
so an index built with one model cannot be reopened with another. That
is enforced loudly here, because mixing embeddings from two models
produces plausible-looking nonsense rather than an error.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import sqlite_vec

SCHEMA_VERSION = 1


class IncompatibleIndexError(RuntimeError):
    pass


@dataclass(frozen=True)
class FrameRecord:
    ts_ms: int
    embedding: np.ndarray
    kept_reason: str


@dataclass(frozen=True)
class Hit:
    video_id: int
    video_path: str
    ts_ms: int
    score: float


@dataclass(frozen=True)
class VideoRow:
    id: int
    path: str
    duration_ms: int
    frame_count: int
    indexed_at: float
    model_id: str
    sampler_config_hash: str


class Store:
    def __init__(self, path: str | Path, embed_dim: int):
        self.path = Path(path)
        self.embed_dim = embed_dim
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.enable_load_extension(True)
        sqlite_vec.load(self._conn)
        self._conn.enable_load_extension(False)
        self._create_schema()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def close(self) -> None:
        self._conn.commit()
        self._conn.close()

    def _create_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS video (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL UNIQUE,
                duration_ms INTEGER NOT NULL,
                fps REAL NOT NULL,
                size_bytes INTEGER NOT NULL,
                mtime REAL NOT NULL,
                indexed_at REAL NOT NULL,
                sampler_config_hash TEXT NOT NULL,
                model_id TEXT NOT NULL,
                score_baseline REAL,
                complete INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS frame (
                id INTEGER PRIMARY KEY,
                video_id INTEGER NOT NULL REFERENCES video(id) ON DELETE CASCADE,
                ts_ms INTEGER NOT NULL,
                kept_reason TEXT NOT NULL,
                ocr_text TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_frame_video ON frame(video_id, ts_ms);
            """
        )

        # Databases written before the completion flag existed predate the
        # fix for interrupted indexing; add the column rather than making
        # the user throw the index away.
        columns = {row["name"] for row in cur.execute("PRAGMA table_info(video)")}
        if "complete" not in columns:
            cur.execute("ALTER TABLE video ADD COLUMN complete INTEGER NOT NULL DEFAULT 0")

        stored_dim = cur.execute(
            "SELECT value FROM meta WHERE key = 'embed_dim'"
        ).fetchone()
        if stored_dim is None:
            cur.execute(
                "INSERT INTO meta(key, value) VALUES ('embed_dim', ?)",
                (str(self.embed_dim),),
            )
            cur.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
        elif int(stored_dim["value"]) != self.embed_dim:
            self._conn.close()
            raise IncompatibleIndexError(
                f"index at {self.path} stores {stored_dim['value']}-dimensional "
                f"vectors, but {self.embed_dim} was requested. Re-index, or "
                f"use a different --db path."
            )

        cur.execute(
            f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_frame USING vec0(
                frame_id INTEGER PRIMARY KEY,
                embedding FLOAT[{self.embed_dim}]
            )
            """
        )
        self._conn.commit()

    def add_video(
        self,
        path: str,
        duration_ms: int,
        fps: float,
        size_bytes: int,
        mtime: float,
        sampler_config_hash: str,
        model_id: str,
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO video(path, duration_ms, fps, size_bytes, mtime,
                              indexed_at, sampler_config_hash, model_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (path, duration_ms, fps, size_bytes, mtime, time.time(),
             sampler_config_hash, model_id),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def mark_complete(self, video_id: int) -> None:
        """Record that every frame of this video made it into the index.

        Until this is called the video counts as needing a re-index, so an
        interrupted run cannot leave a half-indexed video looking finished.
        """
        self._conn.execute("UPDATE video SET complete = 1 WHERE id = ?", (video_id,))
        self._conn.commit()

    def add_frames(self, video_id: int, frames: list[FrameRecord]) -> None:
        if not frames:
            return
        cur = self._conn.cursor()
        for record in frames:
            vector = np.asarray(record.embedding, dtype=np.float32)
            if vector.shape != (self.embed_dim,):
                raise ValueError(
                    f"expected a {self.embed_dim}-dimensional vector, got {vector.shape}"
                )
            cur.execute(
                "INSERT INTO frame(video_id, ts_ms, kept_reason) VALUES (?, ?, ?)",
                (video_id, record.ts_ms, record.kept_reason),
            )
            cur.execute(
                "INSERT INTO vec_frame(frame_id, embedding) VALUES (?, ?)",
                (cur.lastrowid, vector.tobytes()),
            )
        self._conn.commit()

    def search_vector(self, query: np.ndarray, limit: int) -> list[Hit]:
        vector = np.asarray(query, dtype=np.float32)
        rows = self._conn.execute(
            """
            SELECT v.frame_id AS frame_id, v.distance AS distance,
                   f.ts_ms AS ts_ms, f.video_id AS video_id, vid.path AS path
            FROM vec_frame v
            JOIN frame f ON f.id = v.frame_id
            JOIN video vid ON vid.id = f.video_id
            WHERE v.embedding MATCH ? AND k = ?
            ORDER BY v.distance
            """,
            (vector.tobytes(), limit),
        ).fetchall()

        # sqlite-vec reports L2 distance. Both sides are unit vectors, so
        # cosine similarity is recovered exactly as 1 - d^2 / 2.
        return [
            Hit(
                video_id=row["video_id"],
                video_path=row["path"],
                ts_ms=row["ts_ms"],
                score=1.0 - (float(row["distance"]) ** 2) / 2.0,
            )
            for row in rows
        ]

    def needs_reindex(
        self,
        path: str,
        size_bytes: int,
        mtime: float,
        sampler_config_hash: str,
        model_id: str,
    ) -> bool:
        row = self._conn.execute(
            """
            SELECT size_bytes, mtime, sampler_config_hash, model_id, complete
            FROM video WHERE path = ?
            """,
            (path,),
        ).fetchone()
        if row is None:
            return True
        return (
            not row["complete"]
            or row["size_bytes"] != size_bytes
            or abs(row["mtime"] - mtime) > 1e-6
            or row["sampler_config_hash"] != sampler_config_hash
            or row["model_id"] != model_id
        )

    def video_id_for_path(self, path: str) -> int | None:
        row = self._conn.execute(
            "SELECT id FROM video WHERE path = ?", (path,)
        ).fetchone()
        return int(row["id"]) if row else None

    def remove_video(self, video_id: int) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            DELETE FROM vec_frame
            WHERE frame_id IN (SELECT id FROM frame WHERE video_id = ?)
            """,
            (video_id,),
        )
        cur.execute("DELETE FROM frame WHERE video_id = ?", (video_id,))
        cur.execute("DELETE FROM video WHERE id = ?", (video_id,))
        self._conn.commit()

    def list_videos(self) -> list[VideoRow]:
        rows = self._conn.execute(
            """
            SELECT v.id, v.path, v.duration_ms, v.indexed_at, v.model_id,
                   v.sampler_config_hash, COUNT(f.id) AS frame_count
            FROM video v
            LEFT JOIN frame f ON f.video_id = v.id
            GROUP BY v.id
            ORDER BY v.indexed_at DESC
            """
        ).fetchall()
        return [
            VideoRow(
                id=row["id"],
                path=row["path"],
                duration_ms=row["duration_ms"],
                frame_count=row["frame_count"],
                indexed_at=row["indexed_at"],
                model_id=row["model_id"],
                sampler_config_hash=row["sampler_config_hash"],
            )
            for row in rows
        ]

    def stats(self) -> dict[str, int | dict[str, int]]:
        videos = self._conn.execute("SELECT COUNT(*) AS n FROM video").fetchone()["n"]
        frames = self._conn.execute("SELECT COUNT(*) AS n FROM frame").fetchone()["n"]
        by_reason = {
            row["kept_reason"]: int(row["n"])
            for row in self._conn.execute(
                "SELECT kept_reason, COUNT(*) AS n FROM frame GROUP BY kept_reason"
            ).fetchall()
        }
        return {"videos": int(videos), "frames": int(frames), "by_reason": by_reason}
