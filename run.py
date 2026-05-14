import os
_gtk_bin = r"C:\Program Files\GTK3-Runtime Win64\bin"
if os.path.isdir(_gtk_bin) and _gtk_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _gtk_bin + os.pathsep + os.environ.get("PATH", "")

from app import create_app

app = create_app("development")

if __name__ == "__main__":
    app.run(debug=True)
