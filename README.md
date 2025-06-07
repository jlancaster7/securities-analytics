# securities_analytics

## 🚀 Project Setup Instructions

Follow these steps to get up and running with the project. These instructions assume you are starting from scratch with no prior tools installed.

---

## 1. Install Python

Make sure you have **Python 3.8+** installed.

Check your version by running:

```bash
python --version
```
_or_
```bash
python3 --version
```

If you don't have Python installed, download it here:
👉 [https://www.python.org/downloads/](https://www.python.org/downloads/)

---

## 2. Install Poetry

Poetry is used to manage Python packages and virtual environments.

To install Poetry, run the following command in your terminal:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

After installation, **restart your terminal**.

Verify that Poetry is installed:

```bash
poetry --version
```

---

## 3. Unzip the Project

- Unzip the provided `.zip` file.
- Open a terminal and **navigate into the project directory** (where `pyproject.toml` is located).

Example:

```bash
cd path/to/unzipped/project
```

Example:

```bash
cd Downloads/securities_analytics
```

---

## 4. Install Project Dependencies

Inside the project directory, run:

```bash
poetry install
```

This will:
- Create a new virtual environment.
- Install all required dependencies from `pyproject.toml` and `poetry.lock`.

> **Note:** Ignore any `.venv` folder that was included in the zip; Poetry will create a clean new one.

---

## 5. (Optional) Activate the Virtual Environment

If you want to work directly inside the virtual environment:

```bash
poetry shell
```

You can leave the environment anytime by typing:

```bash
exit
```

---

# ✅ That's It!

You're now set up and ready to use the project.

---

## Troubleshooting

- If you get an error about `poetry` not being recognized, double-check that your terminal session was restarted after installing Poetry.
- If Python isn't found, verify that it is installed and added to your system's PATH.

For help, visit:
- [Poetry Documentation](https://python-poetry.org/docs/)
- [Python Downloads](https://www.python.org/downloads/)

---

# 🚀 Happy coding!

