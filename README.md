# 🎲 Random Group Generator

A **Streamlit** web application for creating **transparent and reproducible** random student groups. Perfect for educators, workshop facilitators, and anyone who needs to fairly divide a list of people into groups.

## ✨ Features

- 📤 **Flexible Input**: Upload CSV/TXT files or paste lists directly
- 🎯 **Two Grouping Modes**: 
  - By **number of groups** (e.g., "I need 5 groups")
  - By **group size** (e.g., "I want groups of 4 students each")
- 🔄 **Reproducible Results**: Use seeds to get identical groups every time
- 🧹 **Smart Cleaning**: Automatically removes duplicates and normalizes names
- 📊 **Balanced Distribution**: Round-robin assignment keeps group sizes even
- 📥 **Multiple Export Options**: Download cleaned lists and group assignments
- 🔍 **Full Transparency**: View the exact shuffling sequence used

## 🚀 Getting Started

### Prerequisites

- Python 3.7+
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/students-group-randomizer.git
   cd students-group-randomizer
   ```

2. Install dependencies:
   ```bash
   pip install streamlit
   ```

### Running the Application

```bash
streamlit run app.py
```