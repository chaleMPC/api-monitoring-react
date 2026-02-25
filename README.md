# Setup & Launch

### Clone the repository
git clone https://github.com/MontereyPeninsulaCollege/api-monitoring.git  
cd api-monitoring

### Create a virtual environment
python -m venv .venv

### Activate the virtual environment
.\.venv\Scripts\Activate.ps1

### Install dependencies
pip install -r requirements.txt

### Configure environment variables
Copy .env.example to .env  
Fill in your API keys and credentials.  

### Run the server 
* Make sure the interpreter you are using is your venv not the system python (in vscode, ctrl shift p -> select interpreter -> venv)
* If using vscode just go to run and debug on left sidebar and choose FastAPI(uvicorn) from the drop down
* If you want to launch via cmd you need to let the project read your .env file, using something like this at the top of main.py and then running uvicorn app.main:app --reload
```py
import dotenv
dotenv.load_dotenv()
```
and all the env calls need to be changed from   
`DASH_USER = os.environ["DASH_USER"]`  
to   
`DASH_USER = os.getenv("DASH_USER")`  



### Access the app
Open http://127.0.0.1:8000/  
Login with credentials configured in .env 
