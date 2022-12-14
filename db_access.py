import sqlite3 as SQL
from exceptions import MissingArguments, MatchNotFound
from notetags import Note, NOTAG

# Paths and filenames
DB_PATH: str = ".notes.db"

# Table column names
T_PREP: str = "t_"
N_PREP: str = "n_"


def ex(
        sql: str,
        source: str,
        params: list = None,
        fetchone: bool = False,
        fetchall: bool = False,
        commit: bool = False
) -> list or tuple or None:
    try:
        with SQL.connect(DB_PATH) as dbc:
            if params is not None:
                result: SQL.Cursor = dbc.cursor().execute(sql, params)
            else:
                result: SQL.Cursor = dbc.cursor().execute(sql)
            if commit:
                dbc.commit()

            elif fetchall:
                result: list = result.fetchall()
            elif fetchone:
                result: list or tuple or None = result.fetchone()

    except SQL.Error as e:
        print(f"Problem in db.{source}:")
        print(e)
        return None
    return result


def db_init():
    # todo must make sure db is created in correct place regardless of where qnot is called from
    sql: str = "PRAGMA foreign_keys = ON"
    ex(sql, db_init.__name__)
    create_alltags_table()
    create_notes_table()
    insert_default_tags()


def insert_default_tags():
    sql: str = "INSERT OR IGNORE INTO Tags (tag_id) VALUES ( ? );"
    ex(sql, insert_default_tags.__name__, params=[NOTAG])
    create_tag_table(NOTAG)


def create_notes_table():
    sql: str = """ 
        CREATE TABLE IF NOT EXISTS Notes (
            note_id     TEXT    PRIMARY KEY,
            title       TEXT    DEFAULT NULL,
            body        TEXT    NOT NULL,
            date_c      TEXT    NOT NULL,
            date_m      TEXT    NOT NULL
        ); """
    ex(sql, create_notes_table.__name__)


def create_alltags_table():
    sql: str = """ 
        CREATE TABLE IF NOT EXISTS Tags (
            tag_id      TEXT    PRIMARY KEY
        ); """
    ex(sql, create_alltags_table.__name__)


def create_tag_table(tag: str):
    sql: str = f""" 
        CREATE TABLE IF NOT EXISTS {T_PREP + tag} (
            note_id      TEXT    NOT NULL,
            FOREIGN KEY (note_id)
                REFERENCES Notes (note_id)
                ON DELETE CASCADE
                ON UPDATE SET NULL
            UNIQUE(note_id)
        ); """
    ex(sql, create_tag_table.__name__)


def create_notetags_table(note_id: str):
    sql: str = f""" 
        CREATE TABLE IF NOT EXISTS {N_PREP + note_id} (
            tag_id      TEXT    NOT NULL,
            FOREIGN KEY (tag_id)
                REFERENCES Tags (tag_id)
                ON DELETE CASCADE
        ); """
    ex(sql, create_tag_table.__name__)


def insert_tags_to_notetags(note_id: str, tag: str):
    sql: str = f"""
        INSERT INTO {N_PREP + note_id}
        SELECT tag_id FROM Tags WHERE tag_id = ?; """
    ex(sql, insert_tags_to_notetags.__name__, params=[tag])


def tag_exists(tag: str):
    sql = "SELECT EXISTS(SELECT tag_id FROM Tags WHERE tag_id = ?);"
    res = ex(sql, tag_exists.__name__, params=[tag], fetchone=True)
    if not res or res[0] == 0:
        return False
    return True


def insert_note_to_notes(note: Note):
    sql = """
        INSERT OR REPLACE INTO Notes (
            note_id,
            title,
            body,
            date_c,
            date_m
        ) VALUES ( ?, ?, ?, ?, ? ); """
    ex(
        sql,
        insert_note_to_notes.__name__,
        params=[note.id, note.title, note.body, note.date_c, note.date_m]
    )


# Inserts a single unique tag to table of all tags
def insert_tag_to_tags(tag: str):
    sql = "INSERT OR IGNORE INTO Tags ( tag_id ) VALUES ( ? );"
    ex(sql, insert_tag_to_tags.__name__, params=[tag])


def insert_note_to_tag(note_id: str, tag: str):
    sql = f"INSERT OR IGNORE INTO {T_PREP + tag} (note_id) VALUES ( ? );"
    ex(sql, insert_note_to_tag.__name__, params=[note_id])


def select_notes_tagged_with(tags: list) -> list:
    if tags is None or len(tags) == 0:
        raise MissingArguments(select_notes_tagged_with.__name__)

    for tag in tags:
        if not tag_exists(tag):
            raise MatchNotFound(', '.join(tags))

    sql: str = "SELECT A.note_id, title, body, date_c, date_m FROM Notes A"
    for tag in tags:
        if check_table_exists(T_PREP + tag):
            sql += f" JOIN {T_PREP + tag} ON {T_PREP + tag}.note_id = A.note_id"
    sql += ';'

    return ex(sql, select_notes_tagged_with.__name__, fetchall=True)


def delete_note(note_id, tags: list):
    if not note_id:
        raise MissingArguments({delete_note.__name__})
    sql: str = "DELETE FROM Notes WHERE note_id = ?;"
    ex(sql, delete_note.__name__, params=[note_id], commit=True)
    delete_notetags_table(note_id)
    for tag in tags:
        delete_note_from_tag(note_id, tag)


def delete_notetags_table(note_id: str):
    sql = f"DROP TABLE IF EXISTS {N_PREP + note_id};"
    ex(sql, delete_notetags_table.__name__, commit=True)


def delete_note_from_tag(note_id: str, tag: str):
    if check_table_exists(T_PREP + tag):
        sql: str = f"DELETE FROM {T_PREP + tag} AS T WHERE T.note_id = ?;"
        ex(sql, delete_note_from_tag.__name__, params=[note_id], commit=True)


def select_all_tags_and_count() -> list:
    sql: str = "SELECT tag_id FROM Tags;"
    # todo find way to return count of each tag with notes
    # sql = f"SELECT tag_id, COUNT(SELECT * FROM Notes JOIN {T_PREP + } ON Notes.note_id) FROM Tags;"
    return ex(sql, select_all_tags_and_count.__name__, fetchall=True)


def select_notetags(note_id: str) -> list or None:
    if check_table_exists(N_PREP + note_id):
        sql: str = f"SELECT tag_id FROM {N_PREP + note_id};"
        return ex(sql, select_notetags.__name__, fetchall=True)
    else:
        return None


def select_last_note(num: int) -> list:
    sql: str = "SELECT * FROM Notes ORDER BY ROWID DESC LIMIT ?;"
    return ex(sql, select_last_note.__name__, params=[num], fetchall=True)


def check_table_exists(table_name: str) -> bool:
    sql: str = f"SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
    return len(ex(sql, check_table_exists.__name__, params=[table_name], fetchall=True)) > 0


def select_like(query: list) -> list:
    query_fmt: str = '%' + ' '.join(query) + '%'
    sql: str = "SELECT * FROM Notes WHERE Notes.title LIKE ? OR Notes.body LIKE ?"
    return ex(sql, select_like.__name__, params=[query_fmt, query_fmt], fetchall=True)
