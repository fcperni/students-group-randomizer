# v1.4 - Robust file reading (encoding fallback, separator detection, header override),
#        explicit comma splitting for pasted text, results kept across reruns
import streamlit as st
import codecs
import csv
import io
import random
from math import ceil
from datetime import datetime
from typing import List, Tuple, Dict, Optional

st.set_page_config(page_title="Random Group Generator", page_icon=None, layout="wide")

# ------------------------------
# Constants
# ------------------------------

# Header cells (compared trimmed and lowercase) that mark the first row of a file as a header.
HEADER_KEYWORDS = {
    # English
    "student", "students", "name", "names", "full name", "first name", "last name", "surname",
    "email", "emails", "e-mail", "mail",
    # Spanish
    "alumno", "alumnos", "alumna", "alumnas", "estudiante", "estudiantes", "nombre", "nombres",
    "nombre completo", "apellido", "apellidos", "correo", "correos", "correo electrónico",
}

# Column separators offered for uploaded files. None means "one entry per line".
SEPARATORS: Dict[str, Optional[str]] = {
    "Comma (,)": ",",
    "Semicolon (;)": ";",
    "Tab": "\t",
    "None (one entry per line)": None,
}
AUTO_SEPARATOR = "Auto-detect"

ENCODING_LABELS = {"utf-16": "UTF-16", "utf-8-sig": "UTF-8", "cp1252": "Windows-1252", "latin-1": "Latin-1"}

# ------------------------------
# Utilities
# ------------------------------

def clean_students(raw: List[str]) -> List[str]:
    """Strip, normalize and deduplicate a list of students (names or emails)."""
    students = [s.strip() for s in raw if s and s.strip()]
    seen = set()
    unique = []
    for s in students:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


def decode_bytes(file_bytes: bytes) -> Tuple[str, str]:
    """Decode an uploaded file and return (text, encoding).
    UTF-16 is used when the file starts with a UTF-16 BOM (Excel's "Unicode Text" export).
    Otherwise tries UTF-8 (removing a leading BOM), then Windows-1252 (Excel's default on
    Windows), then Latin-1, which accepts any byte sequence, so decoding never fails or drops
    characters.
    """
    if file_bytes.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return file_bytes.decode("utf-16"), "utf-16"
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return file_bytes.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    return file_bytes.decode("latin-1"), "latin-1"


def detect_delimiter(text: str, sample_size: int = 50) -> Optional[str]:
    """Guess the column separator of a delimited text.
    Tries ';', tab and ',' in that order and returns the first one that splits at least 80% of
    the sampled non-empty lines into the same number (>1) of columns. Semicolons and tabs go
    first because, unlike commas, they rarely appear inside names ("Surname, Name").
    Returns None when no separator fits, i.e. a single-column file.
    """
    lines = [line for line in text.splitlines() if line.strip()][:sample_size]
    if not lines:
        return None
    for delimiter in (";", "\t", ","):
        counts = [len(row) for row in csv.reader(lines, delimiter=delimiter, skipinitialspace=True)]
        most_common = max(set(counts), key=counts.count)
        if most_common > 1 and counts.count(most_common) >= 0.8 * len(counts):
            return delimiter
    return None


def unquote(entry: str) -> str:
    """Remove one pair of enclosing double quotes, CSV style ('""' -> '"'), ignoring surrounding spaces."""
    s = entry.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1].replace('""', '"')
    return entry


def parse_rows(text: str, delimiter: Optional[str]) -> List[List[str]]:
    """Split text into rows of cells, skipping blank lines.
    With delimiter=None each line is a single cell (enclosing double quotes are removed).
    """
    if delimiter is None:
        rows = [[unquote(line)] for line in text.splitlines()]
    else:
        rows = list(csv.reader(io.StringIO(text), delimiter=delimiter, skipinitialspace=True))
    return [row for row in rows if any(cell.strip() for cell in row)]


def normalize_header_cell(cell: str) -> str:
    return cell.replace("﻿", "").strip().lower()


def looks_like_header(row: List[str]) -> bool:
    """True if any cell of the row is a known header keyword (see HEADER_KEYWORDS)."""
    return any(normalize_header_cell(cell) in HEADER_KEYWORDS for cell in row)


def split_header(rows: List[List[str]], has_header: bool) -> Tuple[List[List[str]], List[str]]:
    """Return (data_rows, column_names). Columns without a header name are called col_1, col_2, ..."""
    if not rows:
        return [], []
    n_cols = max(len(row) for row in rows)
    header = rows[0] if has_header else []
    columns = []
    for i in range(n_cols):
        name = header[i].replace("﻿", "").strip() if i < len(header) else ""
        columns.append(name or f"col_{i + 1}")
    return (rows[1:] if has_header else rows), columns


def default_column_index(columns: List[str]) -> int:
    """Index of the first column whose name is a header keyword, or 0."""
    for i, name in enumerate(columns):
        if normalize_header_cell(name) in HEADER_KEYWORDS:
            return i
    return 0


def extract_column(rows: List[List[str]], col_idx: int) -> List[str]:
    col: List[str] = []
    for r in rows:
        if col_idx < len(r):
            col.append(r[col_idx])
    return col


def parse_pasted_text(text: str, split_commas: bool = False) -> List[str]:
    """Split pasted text into entries.
    Line breaks and semicolons always separate entries. Commas only do when split_commas is
    True; double quotes then keep a comma inside a name ("Surname, Name"). Enclosing double
    quotes are removed in both modes.
    """
    items: List[str] = []
    for line in text.splitlines():
        if split_commas:
            for token in next(csv.reader([line], skipinitialspace=True), []):
                items.extend(token.split(";"))
        else:
            items.extend(unquote(part) for part in line.split(";"))
    return items


def assign_groups(students: List[str], n_groups: int, seed: str) -> Tuple[Dict[int, List[str]], List[str]]:
    """Shuffle students with a seeded RNG and deal them round-robin into n_groups.
    Group sizes differ by at most one; the lowest-numbered groups get the extra members.
    Returns (groups_map, shuffled_students).
    """
    rng = random.Random(seed)
    shuffled = students.copy()
    rng.shuffle(shuffled)

    groups: Dict[int, List[str]] = {i + 1: [] for i in range(n_groups)}
    for i, s in enumerate(shuffled):
        groups[(i % n_groups) + 1].append(s)

    return groups, shuffled


def export_groups_csv(groups: Dict[int, List[str]]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["group", "student"])
    for gid, members in groups.items():
        for m in members:
            writer.writerow([gid, m])
    return output.getvalue().encode("utf-8")


# ------------------------------
# UI
# ------------------------------

st.title("Random Group Generator")

st.markdown(
    """
    Build transparent and reproducible random groups.

    How it works:
    1) Upload a CSV/TXT file or paste the list.
    2) Choose Grouping mode: by number of groups or by group size.
    3) (Optional) Set a seed to reproduce results exactly.
    4) Click Generate groups.
    """
)

with st.expander("Input options", expanded=True):
    c1, c2 = st.columns(2)

    with c1:
        uploaded = st.file_uploader("Upload CSV/TXT (single or multiple columns)", type=["csv", "txt"], accept_multiple_files=False)
        file_students: List[str] = []
        if uploaded:
            text, encoding = decode_bytes(uploaded.getvalue())
            detected_delimiter = detect_delimiter(text)
            detected_label = next(label for label, d in SEPARATORS.items() if d == detected_delimiter)
            separator_choice = st.selectbox(
                "Column separator",
                options=[AUTO_SEPARATOR] + list(SEPARATORS),
                format_func=lambda o: f"{o} (detected: {detected_label})" if o == AUTO_SEPARATOR else o,
                help="Choose 'None' if each line is one student, e.g. 'Surname, Name'.",
            )
            delimiter = detected_delimiter if separator_choice == AUTO_SEPARATOR else SEPARATORS[separator_choice]
            rows = parse_rows(text, delimiter)

            if rows:
                has_header = st.checkbox(
                    "First row is a header",
                    value=looks_like_header(rows[0]),
                    key=f"has_header_{uploaded.file_id}_{delimiter!r}",
                    help="Detected automatically. Untick it if the first row is a student.",
                )
                data_rows, columns = split_header(rows, has_header)
                col_idx = 0
                if len(columns) > 1:
                    col_idx = st.selectbox(
                        "Column containing the students/emails",
                        options=list(range(len(columns))),
                        format_func=lambda i: f"{i + 1} - {columns[i]}",
                        index=default_column_index(columns),
                    )
                file_students = extract_column(data_rows, col_idx)

            preview = [s.strip() for s in file_students if s.strip()][:3]
            st.caption(
                f"Read as {ENCODING_LABELS[encoding]}. First entries: "
                + (" · ".join(preview) + " …" if preview else "(none)")
            )

    with c2:
        pasted = st.text_area(
            "Or paste the list (one per line; semicolons also separate entries)",
            placeholder="student1@uni.edu\nstudent2@uni.edu\nLastName1 LastName2, FirstName\n...",
            height=160,
        )
        split_commas = st.checkbox(
            "Commas separate students",
            value=False,
            help='Enable for lists like "a@uni.edu, b@uni.edu". Leave it off for "Surname, Name" entries. '
                 "When enabled, wrap a name in double quotes to keep its comma.",
        )

    source = st.radio("Which source to use?", ["File", "Pasted text"], index=0 if uploaded else 1, horizontal=True)

# Parse students based on source
raw_students: List[str] = []

if source == "File" and uploaded:
    raw_students = file_students
elif source == "Pasted text" and pasted:
    raw_students = parse_pasted_text(pasted, split_commas)

students = clean_students(raw_students)

st.markdown("---")

col_a, col_b, col_c = st.columns([1, 1, 1])
with col_a:
    grouping_mode = st.radio("Group by", options=["Number of groups", "Group size"], horizontal=True)
with col_b:
    seed_default = datetime.now().strftime("%Y-%m-%d")
    seed = st.text_input(
        "Seed (for reproducibility)",
        value=seed_default,
        help="Use any text/number. Same seed + same list + same parameter => identical result."
    )
with col_c:
    sort_display = st.checkbox("Sort members alphabetically (display only)", value=True)

# Parameter inputs depending on mode
param_col = st.columns(1)[0]
if grouping_mode == "Number of groups":
    n_groups_input = param_col.number_input("Number of groups", min_value=1, step=1, value=4)
    desired_group_size = None
else:
    group_size_input = param_col.number_input("Group size (maximum)", min_value=1, step=1, value=4)
    desired_group_size = int(group_size_input)
    n_groups_input = None

st.info(f"Detected students: {len(students)}")
if source == "Pasted text" and not split_commas and any("," in s for s in students):
    st.caption("Some entries contain commas. If commas separate students in your list, tick 'Commas separate students'.")

left, right = st.columns([1, 1])
with left:
    if students:
        st.download_button(
            label="Download cleaned list (TXT)",
            data="\n".join(students).encode("utf-8"),
            file_name="students_clean.txt",
            mime="text/plain",
            use_container_width=True,
        )
with right:
    if students:
        st.caption("Tip: keep the seed you used to replicate the draw later.")

st.markdown("---")

# Validation
ok_inputs = True
warn_msg = None
n_groups = 0

if not students:
    ok_inputs = False
    warn_msg = "You must upload or paste a list of students."
elif grouping_mode == "Number of groups":
    n_groups = int(n_groups_input) if n_groups_input else 0
    if n_groups < 1:
        ok_inputs = False
        warn_msg = "Number of groups must be at least 1."
    elif n_groups > len(students):
        ok_inputs = False
        warn_msg = f"You cannot create {n_groups} groups with only {len(students)} students."
elif not desired_group_size or desired_group_size < 1:
    ok_inputs = False
    warn_msg = "Group size must be at least 1."
else:
    n_groups = ceil(len(students) / desired_group_size)

if warn_msg:
    st.warning(warn_msg)

# A draw is identified by its inputs. Storing them in session_state keeps the results on screen
# across reruns (downloads, display toggles), and comparing them with the current inputs hides
# results that no longer match what the form shows.
current_draw = (tuple(students), n_groups, seed) if ok_inputs else None

# Action button (no 'type' arg for wider Streamlit compatibility)
if st.button("Generate groups", use_container_width=True, disabled=not ok_inputs):
    st.session_state["draw"] = current_draw

last_draw = st.session_state.get("draw")
show_results = last_draw is not None and last_draw == current_draw
if last_draw is not None and not show_results:
    st.info("The inputs changed since the last draw. Click Generate groups to draw again.")

if show_results:
    groups, shuffled = assign_groups(students, n_groups, seed)

    # Transparency panel
    with st.expander("Draw transparency", expanded=False):
        st.write("Seed used:", f"`{seed}`")
        if grouping_mode == "Number of groups":
            st.write("Parameter: Number of groups =", n_groups)
        else:
            st.write("Parameter: Maximum group size =", desired_group_size, " => computed groups =", n_groups)
        st.write("Shuffled order (assignment sequence):")
        st.code("\n".join(shuffled), language="text")

    # Results
    st.subheader("Results")

    sizes = {gid: len(members) for gid, members in groups.items()}
    st.caption("Group sizes distribution")
    size_cols = st.columns(len(sizes))
    for i, (gid, sz) in enumerate(sizes.items()):
        with size_cols[i]:
            st.metric(f"Group {gid}", sz)

    # Group cards
    grid_cols = 3 if len(groups) >= 3 else len(groups)
    cols = st.columns(grid_cols)

    for i, (gid, members) in enumerate(groups.items()):
        shown_members = sorted(members, key=lambda x: x.lower()) if sort_display else members
        with cols[i % grid_cols]:
            st.markdown(f"### Group {gid}")
            if shown_members:
                st.markdown("\n".join([f"- {m}" for m in shown_members]))
            else:
                st.write("(empty)")

    # Downloads
    csv_bytes = export_groups_csv(groups)
    st.download_button(
        label="Download assignment (CSV)",
        data=csv_bytes,
        file_name="groups_assignment.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # Long table preview (student, group)
    st.markdown("---")
    st.markdown("Assignment table")
    tsv_lines = ["student\tgroup"]
    for gid, members in groups.items():
        for m in (sorted(members, key=lambda x: x.lower()) if sort_display else members):
            tsv_lines.append(f"{m}\t{gid}")
    st.code("\n".join(tsv_lines), language="text")

# Footer
st.markdown("---")
with st.expander("Notes & good practices"):
    st.markdown(
        """
        - Reproducibility: same seed, same list (in the same order) and same number of groups => same assignment.
        - Balancing: after shuffling, students are dealt round-robin, so group sizes differ by at most one.
        - Group size mode: the number of groups is ceil(N / size). The size is a maximum: no group is larger,
          but groups may be smaller (e.g. 5 students with size 4 => groups of 3 and 2).
        - Files: the separator, header row and encoding are detected automatically. Check the preview and
          adjust them if needed. If the file has multiple columns, select the correct one.
        - Pasted text: commas only separate students when "Commas separate students" is ticked.
        - Privacy: if you share the screen, prefer emails/anonymous IDs.
        """
    )
