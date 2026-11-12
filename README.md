# 🎲 Random Group Generator

A **Streamlit** web application for creating **transparent and reproducible** random student groups. Perfect for educators, workshop facilitators, and anyone who needs to fairly divide a list of people into groups.

## ✨ Features

- 📤 **Flexible Input**: Upload CSV/TXT files or paste lists directly
- 🧾 **Smart File Reading**: Detects the encoding, column separator and header row, with manual overrides and a preview
- 🎯 **Two Grouping Modes**: 
  - By **number of groups** (e.g., "I need 5 groups")
  - By **group size** (e.g., "I want groups of at most 4 students each")
- 🔄 **Reproducible Results**: Use seeds to get identical groups every time
- 🧹 **Smart Cleaning**: Trims whitespace, drops empty entries and removes case-insensitive duplicates
- 📊 **Balanced Distribution**: Round-robin assignment keeps group sizes within one member of each other
- 📥 **Export**: Download the cleaned list (TXT) and the group assignment (CSV)
- 🔍 **Full Transparency**: View the exact shuffling sequence used

## 🚀 Getting Started

### Prerequisites

- Python 3.8+ (the minimum for Streamlit 1.28; Streamlit excludes Python 3.9.7). Current Streamlit releases require Python 3.11+, so a recent Python version is recommended.
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/fcperni/students-group-randomizer.git
   cd students-group-randomizer
   ```

2. (Recommended) Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

```bash
streamlit run app.py
```

Streamlit opens the app in your browser, by default at <http://localhost:8501>.

> Last verified with Python 3.14 and Streamlit 1.67.

## 📖 Usage

1. **Provide the list** in the *Input options* panel, either by:
   - **uploading a `.csv` / `.txt` file**. The app detects the encoding, the column separator and whether the first row is a header, and shows the first entries it read. If the preview looks wrong, adjust *Column separator* or *First row is a header*. If the file has several columns, choose the one that contains the students; or
   - **pasting the list** into the text area. Tick *Commas separate students* only if commas separate people (e.g. `a@uni.edu, b@uni.edu`).

   If you provide both, pick one with *Which source to use?* (it defaults to *File* when a file is uploaded).
2. **Check the *Detected students* counter**, which counts students after cleaning. You can download the cleaned list as `students_clean.txt`.
3. **Choose *Group by***: *Number of groups* or *Group size (maximum)*, then set the value (default: 4).
4. **Keep or change the *Seed***. It defaults to today's date (`YYYY-MM-DD`).
5. **Click *Generate groups***.

The results show:

- the size of each group;
- one card per group, with members optionally sorted alphabetically;
- a **Download assignment (CSV)** button;
- a plain-text `student → group` table you can copy.

The collapsible ***Draw transparency*** panel shows the seed, the parameter used and the complete shuffled order.

Results stay on screen while you download files or change display options. As soon as the list, the seed or the number of groups changes, they are hidden and a notice asks you to generate the groups again, so the groups on screen always match the current inputs.

## 📂 Input Formats

### Files (CSV / TXT)

- **Encoding**: UTF-8 (with or without BOM) and UTF-16 with BOM (Excel's *Unicode Text*) are detected. Any other file is read as Windows-1252 (Excel's default on Windows) or, if that fails, as Latin-1, which accepts any byte. The encoding used is shown under the uploader.
- **Column separator**: auto-detected among `;`, tab and `,`, in that order. The first one that splits at least 80% of the lines into the same number of columns (more than one) wins; if none does, each line is a single entry. You can override it with *Column separator*, where *None (one entry per line)* treats every line as one student. In that mode, enclosing double quotes (`"García, Ana"`) are removed.
- **Header row**: detected when any cell of the first row, ignoring case and surrounding spaces, is one of these keywords:
  - English: `student`, `students`, `name`, `names`, `full name`, `first name`, `last name`, `surname`, `email`, `emails`, `e-mail`, `mail`
  - Spanish: `alumno`, `alumnos`, `alumna`, `alumnas`, `estudiante`, `estudiantes`, `nombre`, `nombres`, `nombre completo`, `apellido`, `apellidos`, `correo`, `correos`, `correo electrónico`

  Override it with *First row is a header*. Without a header, columns are named `col_1`, `col_2`, …
- **Column**: when there are several columns, the first one whose header is a keyword is preselected (otherwise the first column). Blank lines and rows that don't reach the selected column are skipped.

```csv
Nombre;Correo
"García López, Ana";ana.garcia@uni.edu
"Pérez Ruiz, Luis";luis.perez@uni.edu
```

### Pasted text

- **Line breaks and semicolons** always separate entries.
- **Commas** only separate entries when *Commas separate students* is ticked. In that case, wrap a name in double quotes to keep its comma. If the option is off and some entry contains a comma, the app shows a hint.
- **Enclosing double quotes** are removed in both modes.

With the option off (default), this is 4 students:

```text
García López, Ana
Pérez Ruiz, Luis
eva@uni.edu; juan@uni.edu
```

With the option on, this is 3 students:

```text
eva@uni.edu, juan@uni.edu, "García López, Ana"
```

### Cleaning

After reading the list, the app trims each entry, drops empty ones and removes duplicates **case-insensitively** (`Ana` and `ana ` count as the same person). The first spelling found is kept and the original order is preserved. Names are not modified in any other way.

## ⚙️ How Grouping Works

1. The cleaned list is shuffled with Python's `random.Random(seed)`.
2. Students are dealt **round-robin** in shuffled order: 1st → Group 1, 2nd → Group 2, … starting again at Group 1 after the last group.

As a result, group sizes differ by **at most one**, and the extra members go to the lowest-numbered groups.

- **Number of groups** creates exactly that many groups. It cannot be greater than the number of students.
- **Group size (maximum)** creates `ceil(N / size)` groups, where `N` is the number of students. No group is larger than the size, but groups can be noticeably smaller when `N` is not a multiple of it:

| Students | Maximum size | Groups created | Resulting sizes |
|---------:|-------------:|---------------:|-----------------|
| 12       | 4            | 3              | 4, 4, 4         |
| 10       | 4            | 3              | 4, 3, 3         |
| 9        | 4            | 3              | 3, 3, 3         |
| 5        | 4            | 2              | 3, 2            |

## 🔄 Reproducibility

You get the same groups only if **all** of these match:

- the **seed**, as exactly the same text;
- the **cleaned list, in the same order**: reordering the input changes the draw;
- the resulting **number of groups**.

Because the default seed is today's date, repeating a draw on the same day with the same input gives the same result, but on another day it won't unless you type the original seed. Write the seed down (it is shown in *Draw transparency*) to be able to replicate or audit a draw later.

The shuffling and assignment are the same as in earlier versions of the app, so the same cleaned list, seed and number of groups still give the same groups. The cleaned list itself may differ for the same input, though: pasted commas no longer split entries by default (tick *Commas separate students* if your list relied on them), and files are now read more accurately (encoding, separator and header row). To replicate an old draw, compare the *Detected students* count and the cleaned list with the original ones.

Python's documentation only guarantees that `random()` keeps producing the same sequence across Python versions; the shuffling algorithm is not formally guaranteed to stay the same. For long-term audits, record the Python version used along with the seed.

## 📥 Exports

| File | Content |
|------|---------|
| `students_clean.txt` | Cleaned list, one student per line, in input order. |
| `groups_assignment.csv` | Columns `group,student`, one row per student. Members appear in draw order. |

```csv
group,student
1,Juan
1,Luis
2,Ana
2,Eva
```

The *Sort members alphabetically* option only affects what is shown on screen (group cards and assignment table), not the CSV export.

## ⚠️ Known Limitations

- **Separator detection is a heuristic.** A one-column file whose lines look like `Surname, Name` is detected as two comma-separated columns. Choose *None (one entry per line)* in *Column separator*.
- **Header detection only knows the keywords listed above.** For any other header, tick *First row is a header* manually.
- **Other encodings** (e.g. Mac Roman, or UTF-16 without BOM) are read as Windows-1252, so some characters may look wrong, although none are dropped. Check the preview and re-save the file as *CSV UTF-8* if needed.
- **Semicolons always separate pasted entries**, even inside double quotes.

## 🔒 Privacy

The app's code does not save the list or the results anywhere and keeps no history of previous draws. If you deploy it to a shared server, the list is sent to that server. When projecting your screen, prefer emails or anonymous IDs over full names.

## 🗂️ Project Structure

```text
students-group-randomizer/
├── app.py            # Streamlit app: input parsing, cleaning, grouping and UI
├── requirements.txt  # Python dependencies (streamlit>=1.28.0)
├── README.md
├── .gitignore
└── .idea/            # PyCharm project settings
```

Main functions in `app.py`:

| Function | Purpose |
|----------|---------|
| `decode_bytes` | Decodes the uploaded file (UTF-16 with BOM, UTF-8, Windows-1252, Latin-1) and reports the encoding used. |
| `detect_delimiter` | Guesses the column separator (`;`, tab or `,`) or returns `None` for a single-column file. |
| `parse_rows` / `unquote` | Split the text into rows of cells, skipping blank lines; in one-entry-per-line mode, remove enclosing double quotes. |
| `looks_like_header` / `split_header` | Detect a header row and return the data rows plus column names. |
| `default_column_index` | Preselects the first column whose header is a known keyword. |
| `extract_column` | Extracts the selected column from the parsed rows. |
| `parse_pasted_text` | Splits pasted text on line breaks, semicolons and, optionally, commas. |
| `clean_students` | Trims entries, drops empty ones and removes case-insensitive duplicates. |
| `assign_groups` | Seeded shuffle followed by round-robin assignment. |
| `export_groups_csv` | Builds the `group,student` CSV export. |
