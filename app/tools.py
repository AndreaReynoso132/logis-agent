from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_google_genai import ChatGoogleGenerativeAI
from database import DB_PATH

db  = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}", include_tables=["productos", "feedback"])
llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=1.0)

toolkit = SQLDatabaseToolkit(db=db, llm=llm)
TOOLS   = toolkit.get_tools()