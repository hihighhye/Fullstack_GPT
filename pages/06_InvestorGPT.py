import streamlit as st
from langchain.chat_models import ChatOpenAI
from typing import Type
from langchain.tools import Tool, BaseTool
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from langchain.agents import initialize_agent, AgentType
from langchain.tools import DuckDuckGoSearchResults
import requests
import os


alpha_vantage_api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")

llm = ChatOpenAI(
    temperature=0.1,
    model_name="gpt-4o-mini"
)


st.set_page_config(
    page_title="InvestorGPT",
    page_icon="📉"
)

st.title("InvestorGPT")

st.markdown(
    """
    # InvestorGPT

    Welcome to InvestorGPT.

    Write down the name of a company 
    and our Agent will do the research for you.
    """
)


class StockMarketSymbolSearchToolArgsSchema(BaseModel):
    query:str = Field(description="The query you will search for")

class StockMarketSymbolSearchTool(BaseTool):
    name:str = "StockMarketSymbolSearchTool"
    description:str = """
        Use this tool to find the stock market symbol for a company.
        It takes a query as an argument.
        Example query: Stock Market Symbol for Apple Company
    """

    args_schema: Type[StockMarketSymbolSearchToolArgsSchema] = StockMarketSymbolSearchToolArgsSchema

    def _run(self, query):
        ddg = DuckDuckGoSearchResults()
        return ddg.run(query)

class CompanyOverviewToolArgsSchema(BaseModel):
    symbol:str = Field(description="Stock Symbol of the company.\
                       Example: AAPL, TSLA")

class CompanyOverviewTool(BaseTool):
    name:str = "CompanyOverview"
    description:str = """
    Use this to get an overview of the financials of the company.
    You should enter a stock symbol.
    """
    args_schema: type[CompanyOverviewToolArgsSchema] = CompanyOverviewToolArgsSchema

    def _run(self, symbol):
        r = requests.get(f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={alpha_vantage_api_key}")
        return r.json()
    
class CompanyIncomeStatementTool(BaseTool):
    name:str = "CompanyIncomeStatement"
    description:str = """
    Use this to get the income statement of the financials of the company.
    You should enter a stock symbol.
    """
    args_schema: type[CompanyOverviewToolArgsSchema] = CompanyOverviewToolArgsSchema

    def _run(self, symbol):
        r = requests.get(f"https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={symbol}&apikey={alpha_vantage_api_key}")
        return r.json()['annualReports']

class CompanyStockPerformanceTool(BaseTool):
    name:str = "CompanyStockPerformance"
    description:str = """
    Use this to get the weekly performance of the financials of the company.
    You should enter a stock symbol.
    """
    args_schema: type[CompanyOverviewToolArgsSchema] = CompanyOverviewToolArgsSchema

    def _run(self, symbol):
        r = requests.get(f"https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol={symbol}&apikey={alpha_vantage_api_key}")
        response = r.json()
        recent_result = list(response["Weekly Time Series"].items())[:200]
        
        return recent_result
    

agent = initialize_agent(
    llm=llm, 
    verbose=True,
    agent=AgentType.OPENAI_FUNCTIONS,
    handle_parsing_errors=True,
    tools=[
        StockMarketSymbolSearchTool(),
        CompanyOverviewTool(),
        CompanyIncomeStatementTool(),
        CompanyStockPerformanceTool(),
    ],
    agent_kwargs={
        "system_message": SystemMessage(content="""
            You are a hedge fund manager.
            
            You evaluate a company and provide your opinion and reasons why
            the stock is a buy or not.
                                        
            Consider the performance of a stock, the company overview and the
            income statement.
                                        
            Be assertive in your judgement and recommand the stock or advise
            the user against it.
        """)
    }
)

# prompt = "Give me information on Cloudflare's stock, considering its financials, income statements, \
#     and weekly stock performances. Help me analyze if it's a potential good investment."

# agent.invoke(prompt)

company = st.text_input("Write the name of company that you are interested in.")

if company:
    result = agent.invoke(company)
    st.write(result["output"].replace("$", "\$"))