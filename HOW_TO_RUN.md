# How to Run the Project Phase 1 Demo

To run the full-stack simulation of Project Phase 1 locally on your machine, follow these steps in your terminal:

### Step 1: Open Terminal
Open your Command Prompt, PowerShell, or VS Code terminal.

### Step 2: Navigate to the Backend Directory
You need to be in the `backend` folder where the FastAPI server (`main.py`) is located.
```bash
cd "e:\project phase 1\zarkaan\backend"
```

### Step 3: Install Required Packages
Make sure you have `fastapi` and `uvicorn` installed. These are the tools used to host the local web server.
```bash
pip install fastapi uvicorn
```

### Step 4: Start the Server
Run the FastAPI application. The `--reload` flag means the server will automatically update if you change any code.
```bash
python -m uvicorn main:app --reload
```

### Step 5: View the App in your Browser
Once the server is running, it will print a message saying it's listening on `http://0.0.0.0:8000`.
Open your web browser (Chrome/Edge/Firefox) and go to:
**http://localhost:8000/dashboard.html**

---

*To stop the server at any time, go back to your terminal and press `Ctrl + C`.*
