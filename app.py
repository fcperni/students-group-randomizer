# v1.3 - Fix placeholder string (use \n escapes), remove Streamlit button 'type' for wider compatibility
import streamlit as st
import csv
import io
import random
from math import ceil
from datetime import datetime
from typing import List, Tuple, Dict

st.set_page_config(page_title="Random Group Generator", page_icon=None, layout="wide")

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


def read_csv_bytes(file_bytes: bytes) -> Tuple[List[List[str]], List[str]]:
    """Read a CSV/TXT and return (rows, detected_header_names).
    If there is a single column, that's used. If multiple, user will select one.
    """
    text = file_bytes.decode("utf-8", errors="ignore")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], []

    header = rows[0]
    looks_like_header = any(h.lower() in {"student", "students", "name", "names", "email", "emails"} for h in header)
    if looks_like_header:
        columns = [h.strip() or f"col_{i+1}" for i, h in enumerate(header)]
        data_rows = rows[1:]
    else:
        columns = [f"col_{i+1}" for i in range(len(header))]
        data_rows = rows

    return data_rows, columns


def extract_column(rows: List[List[str]], col_idx: int) -> List[str]:
    col: List[str] = []
    for r in rows:
        if col_idx < len(r):
            col.append(r[col_idx])
    return col


def assign_groups(students: List[str], n_groups: int, seed: str, balance_mode: str = "round_robin") -> Tuple[Dict[int, List[str]], List[str]]:
    """Shuffle students and split into n_groups in a balanced way.
    Returns (groups_map, shuffled_students).
    """
    rng = random.Random(seed)
    shuffled = students.copy()
    rng.shuffle(shuffled)

    groups: Dict[int, List[str]] = {i + 1: [] for i in range(n_groups)}
    if balance_mode == "round_robin":
        for i, s in enumerate(shuffled):
            gid = (i % n_groups) + 1
            groups[gid].append(s)
    else:
        for i, s in enumerate(shuffled):
            gid = (i % n_groups) + 1
            groups[gid].append(s)

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
    1) Upload a CSV/TXT with the list (one column) or paste the list.
    2) Choose Grouping mode: by number of groups or by group size.
    3) (Optional) Set a seed to reproduce results exactly.
    4) Click Generate groups.
    """
)

with st.expander("Input options", expanded=True):
    c1, c2 = st.columns(2)

    with c1:
        uploaded = st.file_uploader("Upload CSV/TXT (single or multiple columns)", type=["csv", "txt"], accept_multiple_files=False)
        csv_rows: List[List[str]] = []
        detected_columns: List[str] = []
        selected_col = None
        if uploaded:
            csv_rows, detected_columns = read_csv_bytes(uploaded.getvalue())
            if detected_columns:
                selected_col = st.selectbox(
                    "If your CSV has multiple columns, choose the one containing students/emails",
                    options=[(i, name) for i, name in enumerate(detected_columns)],
                    format_func=lambda x: f"{x[0] + 1} - {x[1]}",
                    index=0
                )

    with c2:
        pasted = st.text_area(
            "Or paste the list (one per line or comma/semicolon-separated)",
            placeholder="student1@uni.edu\nstudent2@uni.edu\nLastName1 LastName2, FirstName\n...",
            height=160,
        )

    source = st.radio("Which source to use?", ["File", "Pasted text"], index=0 if uploaded else 1, horizontal=True)

# Parse students based on source
raw_students: List[str] = []

if source == "File" and uploaded:
    if csv_rows:
        if selected_col is not None:
            idx = selected_col[0]
            raw_students = extract_column(csv_rows, idx)
        else:
            raw_students = extract_column(csv_rows, 0)
elif source == "Pasted text" and pasted:
    if ";" in pasted or "," in pasted:
        items: List[str] = []
        for line in pasted.splitlines():
            for part in csv.reader([line], delimiter=',', quotechar='"'):
                for token in part:
                    for sub in token.split(";"):
                        if sub is not None:
                            items.append(sub)
        raw_students = items
    else:
        raw_students = pasted.splitlines()

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
    group_size_input = param_col.number_input("Group size (target)", min_value=1, step=1, value=4)
    desired_group_size = int(group_size_input)
    n_groups_input = None

st.info(f"Detected students: {len(students)}")

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

if not students:
    ok_inputs = False
    warn_msg = "You must upload or paste a list of students."
else:
    if grouping_mode == "Number of groups":
        n_groups = int(n_groups_input) if n_groups_input else 0
        if n_groups < 1:
            ok_inputs = False
            warn_msg = "Number of groups must be at least 1."
        elif n_groups > len(students):
            ok_inputs = False
            warn_msg = f"You cannot create {n_groups} groups with only {len(students)} students."
    else:
        n_groups = ceil(len(students) / desired_group_size) if desired_group_size else 0
        if not desired_group_size or desired_group_size < 1:
            ok_inputs = False
            warn_msg = "Group size must be at least 1."
        elif n_groups < 1:
            ok_inputs = False
            warn_msg = "Invalid group size."

if warn_msg:
    st.warning(warn_msg)

# Action button (no 'type' arg for wider Streamlit compatibility)
btn = st.button("Generate groups", use_container_width=True, disabled=not ok_inputs)

if btn and ok_inputs:
    groups, shuffled = assign_groups(students, int(n_groups), seed)

    # Transparency panel
    with st.expander("Draw transparency", expanded=False):
        st.write("Seed used:", f"`{seed}`")
        if grouping_mode == "Number of groups":
            st.write("Parameter: Number of groups =", n_groups)
        else:
            st.write("Parameter: Target group size =", desired_group_size, " => computed groups =", n_groups)
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
        - Reproducibility: same seed, same list and same parameter => same assignment.
        - Balancing: we use a round-robin distribution after shuffling to keep sizes as even as possible.
        - Privacy: if you share the screen, prefer emails/anonymous IDs.
        - CSV: if your CSV has multiple columns, select the correct one.
        - Group size mode: we compute the number of groups as ceil(N / size); last groups may have one less member.
        """
    )
