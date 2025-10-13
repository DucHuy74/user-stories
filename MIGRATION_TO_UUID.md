Migration notes: Converting project IDs to UUIDs

What changed
- All primary keys and foreign key references in `models.py` were converted from Integer to `String(36)` and a default UUID generator was added so new rows auto-generate UUIDs.
- `story_id` (external id) is now a UUID string by default.
- `analyzeUserStory/phase1.py`, `phase2.py`, and `phase3.py` code updated to generate and accept UUID strings for story and session ids.
- Parsing of `usid_text` was made robust by splitting only on the first `:`.

Database migration steps (MySQL)
1. Backup your database before making changes.
2. If you have existing data you want to keep, you'll need to:
   - Add new UUID columns alongside existing integer PKs (e.g., `id_new VARCHAR(36)`),
   - Populate them with generated UUIDs for existing rows (`UPDATE table SET id_new = UUID()`),
   - Update all FK columns similarly, mapping old integer IDs to the new UUIDs.
   - Drop old integer columns and rename the new columns to `id`.

Quick approach for clean slate
- If you can drop existing data, simply drop and recreate the database/tables. The SQLAlchemy `create_all()` will now create UUID PKs and defaults.

Notes and caveats
- If other systems integrate with this DB and expect integer IDs, coordinate migration to avoid breaking integrations.
- Foreign key migration requires careful ordering to keep referential integrity.
- Consider using Alembic for a controlled migration path.

If you want, I can:
- Create Alembic migration stubs to help automate the change.
- Generate SQL snippets for migrating each table in place (requires mapping of existing rows).
- Run basic smoke tests to confirm app starts and new inserts generate UUIDs.
