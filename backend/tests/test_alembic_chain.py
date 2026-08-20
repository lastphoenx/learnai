"""Alembic-Revisionskette muss beim API-Start durchlaufbar sein."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_revision_chain_is_connected():
    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1, f"expected single head, got {heads}"
    for rev in script.walk_revisions(base="base", head=heads[0]):
        if rev.down_revision is None:
            continue
        down = rev.down_revision if isinstance(rev.down_revision, str) else rev.down_revision[0]
        script.get_revision(down)
