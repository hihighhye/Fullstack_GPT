import streamlit as st
from langchain.tools import DuckDuckGoSearchResults
import yfinance
import json
import openai
import datetime
import sqlite3


@st.cache_resource()
def initialize_db():
    con = sqlite3.connect("company_report.db")
    cur = con.cursor()

    cur.execute("""
                CREATE TABLE IF NOT EXISTS saved_reports (
                    company text not null,
                    search_date date not null,
                    content text not null,
                    primary key (company, search_date)
                );
    """)

    con.close()

def get_saved_reports():
    con = sqlite3.connect("company_report.db")
    cur = con.cursor()

    res = cur.execute("""
        SELECT company, search_date, content FROM saved_reports;
    """)
    return res.fetchall()

def get_ticker(inputs):
    ddg = DuckDuckGoSearchResults()
    company_name = inputs["company_name"]
    return ddg.run(f"Ticker symbol of {company_name}")

def get_income_statement(inputs):
    ticker = inputs["ticker"]
    stock = yfinance.Ticker(ticker)
    return json.dumps(stock.income_stmt.to_json())

def get_balance_sheet(inputs):
    ticker = inputs["ticker"]
    stock = yfinance.Ticker(ticker)
    return json.dumps(stock.balance_sheet.to_json())

def get_daily_stock_performance(inputs):
    ticker = inputs["ticker"]
    stock = yfinance.Ticker(ticker)
    return json.dumps(stock.history(period="3mo").to_json())

def find_record(company, search_date):
    con = sqlite3.connect("company_report.db")
    cur = con.cursor()

    saved_list = get_saved_reports()
    for record in saved_list:
        if record[0] == company and record[1] == search_date:
            con.close()
            return record[2]
    con.close()
    return None

def save_report(company, search_date, content):
    if find_record(company, search_date) == None:
        con = sqlite3.connect("company_report.db")
        cur = con.cursor()

        res = cur.execute("""
                        INSERT INTO saved_reports(company, search_date, content) 
                        VALUES (?, ?, ?);
                        """, (company, search_date, content))
        con.commit()
        con.close()
        st.toast("Saved!")

def delete_report(company, search_date):
    if find_record(company, search_date) != None:
        con = sqlite3.connect("company_report.db")
        cur = con.cursor()

        res = cur.execute(f"""
            DELETE FROM saved_reports 
            WHERE company='{company}' and search_date='{search_date}';
        """)
        con.commit()
        con.close()
        st.toast("Deleted!")

def print_report(company, search_date, messages, stored=False):
    with st.container():
        st.header(f"Report for {company}", divider="grey")
        content = messages
        if not stored:
            content = messages[-1].content[0].text.value
        col1, col2, _col3, _col4, col5 = st.columns(5)
        col1.write(f"Research Date: ")
        col2.write(f"{search_date}")
        if not stored:
            saved = col5.button("Save", type="primary")
            if saved:
                save_report(company, search_date, content)
        else:
            deleted = col5.button("Delete", type="primary")
            if deleted:
                delete_report(company, search_date)
      
        st.write(content.replace("$", "\$"))

def get_messages(thread_id):
    messages = openai.beta.threads.messages.list(
        thread_id=thread_id
    )
    messages = list(messages)
    messages.reverse()
  
    return messages

def send_message(thread_id, content):
    return openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=content,
    )

def run_thread(assistant_id, thread_id):
    return openai.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id
            )
    
def get_run(run_id, thread_id):
    return openai.beta.threads.runs.retrieve(
        run_id=run_id,
        thread_id=thread_id
    )

def get_tool_outputs(run_id, thread_id):
    run = get_run(run_id, thread_id)
    outputs = []
    for action in run.required_action.submit_tool_outputs.tool_calls:
        action_id = action.id
        function = action.function
        outputs.append({
            "output": functions_map[function.name](json.loads(function.arguments)),
            "tool_call_id": action_id,
        })

    return outputs

def submit_tool_outputs(run_id, thread_id):
    outputs = get_tool_outputs(run_id, thread_id)
    return openai.beta.threads.runs.submit_tool_outputs(
        run_id=run_id,
        thread_id =thread_id,
        tool_outputs=outputs,
    )

@st.cache_resource()
def create_assistant():
    assistant = openai.beta.assistants.create(
                    name="Streamlit - Investor Assistant",
                    instructions="You help users do research on publicly traded companies \
                        and you help them decide if they should buy the stock or not.",
                    model="gpt-4o-mini",
                    tools=functions,
                )
    return assistant

def create_thread(query):
    thread = openai.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": query
                    }
                ]
            )
    return thread

# @st.cache_resource(show_spinner=False)
def generate_report(company, search_date):
    company = company.upper()
    if (company, search_date) not in st.session_state["search_history"].keys():
        with st.status("Generating report...") as prog:
            # Create thread and execute the first run for the thread.
            query = f"I want to know if {company} stock is a good buy"
            thread = create_thread(query)
            run = run_thread(assistant.id, thread.id)

            # Communicate with Assistant until getting the final response.
            while (True):
                thread_status = get_run(run.id, thread.id).status
                if thread_status == "completed":
                    prog.update(label="Completed", state="complete")
                    break
                else:
                    if thread_status == "requires_action":
                        run = submit_tool_outputs(run.id, thread.id)
    
        messages = get_messages(thread.id)
        st.session_state["search_history"][(company, search_date)] = messages
    
    else:
        messages = st.session_state["search_history"][(company, search_date)]

    return company, messages


functions_map = {
    "get_ticker": get_ticker,
    "get_income_statement": get_income_statement,
    "get_balance_sheet": get_balance_sheet,
    "get_daily_stock_performance": get_daily_stock_performance,
}

functions = [
    {
        "type": "function",
        "function": {
            "name": "get_ticker",
            "description": "Given the name of a company returns its ticker symbol. \
                Do NOT append any other comment except the ticker symbol. (e.g. AAPL)",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "The name of the company"
                    }
                },
                "required": ["company_name"],
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_income_statement",
            "description": "Given a ticker symbol (i.e AAPL)\
                returns the company's income statement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Ticker symbol of the company"
                    }
                },
                "required": ["ticker"],
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_balance_sheet",
            "description": "Given a ticker symbol (i.e AAPL)\
                return the company's balance sheet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Ticker symbol of the company"
                    }
                },
                "required": ["ticker"],
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_stock_performance",
            "description": "Given a ticker symbol (i.e AAPL)\
                return the performance of the stock for the last 100 days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Ticker symbol of the company"
                    }
                },
                "required": ["ticker"],
            }
        }
    },
]



st.set_page_config(
    page_title="InvestorGPT with Yahoo Finance",
    page_icon="📊"
)

st.title("InvestorGPT")

st.markdown(
    """
    # InvestorGPT with Yahoo Finance
    ---

    Welcome to InvestorGPT.

    Click the sidebar and write down the name of a company

    then our Assistant will give a report for you.

    All information is based on Yahoo Finance.
    """
)

st.divider()

initialize_db()

if "search_history" not in st.session_state:
    st.session_state["search_history"] = dict()

assistant = create_assistant()
today = datetime.date.today()

search_tab, listup_tab = st.tabs(["Search", "My List"])

with search_tab:
    company = st.text_input("The name of company")

    if company:
        company, messages = generate_report(company, today)
        print_report(company, today, messages)

with listup_tab:
    saved_list = get_saved_reports()
    if saved_list:
        company_map = {i: saved_list[i][0] for i in range(len(saved_list))}
        selected = st.pills(
            "Reports that you've saved", 
            options=company_map.keys(), 
            format_func=lambda option: company_map[option], 
            selection_mode="single"
        )

        if selected != None:
            company, search_date, content = saved_list[selected]
            print_report(company, search_date, content, stored=True)
    
    else:
        st.write("None of financial reports has been saved.")

               