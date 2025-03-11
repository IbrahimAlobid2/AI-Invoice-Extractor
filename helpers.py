
from pypdf import PdfReader
import pandas as pd
import re
from langchain.prompts import PromptTemplate
from langchain.agents.agent_types import AgentType
from ast import literal_eval
import os
from dotenv import find_dotenv, load_dotenv
from langchain_groq import ChatGroq
from io import BytesIO
from pypdf import PdfReader
import pandas as pd
import re
from ast import literal_eval


load_dotenv()
GROQ_API = os.getenv("GROQ_API_KEY")
model_name = 'llama-3.3-70b-versatile'
llm  =  ChatGroq(api_key=GROQ_API,
    model_name=model_name,
    temperature=0.0,
    
)

# Modified PDF text extraction function
def get_pdf_text(uploaded_file):
    text = ""
    # Create a bytes stream from uploaded file
    pdf_bytes = BytesIO(uploaded_file.getvalue())
    pdf_reader = PdfReader(pdf_bytes)
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text
	

def extracted_data(pages_data):
	template = """Extract all the following values: Invoice ID, DESCRIPTION, Issue Date, 
		UNIT PRICE, AMOUNT, Bill For, From, and Terms from: {pages}
	
		Expected output format (REMOVE DOLLAR SIGNS AND COMMAS):
		{{
			'Invoice ID': '1001329',
			'DESCRIPTION': 'Professional Services',
			'Issue Date': '5/4/2023',
			'UNIT PRICE': '100.00',
			'AMOUNT': '1100.00',
			'Bill For': 'James',
			'From': 'Excel Company',
			'Terms': 'Due on receipt'
		}}"""
	prompt_template = PromptTemplate(input_variables=["pages"], template=template)
	response = llm.invoke(prompt_template.format(pages=pages_data))
	return response.content
	

def clean_currency(value):
    if isinstance(value, str):
        return float(value.replace('$', '').replace(',', '').strip())
    return value

def create_docs(user_pdf_list):
    # Initialize DataFrame with proper types
    df = pd.DataFrame({
        'Invoice ID': pd.Series(dtype='str'),
        'DESCRIPTION': pd.Series(dtype='str'),
        'Issue Date': pd.Series(dtype='str'),
        'UNIT PRICE': pd.Series(dtype='float'),
        'AMOUNT': pd.Series(dtype='float'),
        'Bill For': pd.Series(dtype='str'),
        'From': pd.Series(dtype='str'),
        'Terms': pd.Series(dtype='str')
    })

    for filename in user_pdf_list:
        try:
            raw_data = get_pdf_text(filename)
            llm_extracted_data = extracted_data(raw_data)
            
            # Extract content between curly braces
            pattern = r'{(.+?)}'
            match = re.search(pattern, llm_extracted_data, re.DOTALL)
            
            if not match:
                print("No valid data found in LLM output")
                continue
                
            extracted_text = match.group(1).strip()
            
            try:
                # Safely evaluate the string to dictionary
                data_dict = literal_eval('{' + extracted_text + '}')
                
                # Clean currency fields
                for money_col in ['UNIT PRICE', 'AMOUNT']:
                    if money_col in data_dict:
                        data_dict[money_col] = clean_currency(data_dict[money_col])
                
                # Handle key mismatches
                if 'Date' in data_dict and 'Issue Date' not in data_dict:
                    data_dict['Issue Date'] = data_dict.pop('Date')
                
                # Add to DataFrame
                df = pd.concat([df, pd.DataFrame([data_dict])], ignore_index=True)
                
            except (SyntaxError, ValueError, KeyError) as e:
                print(f"Error processing extracted data: {e}")
                continue
                
        except Exception as e:
            print(f"Error processing file {filename}: {e}")
            continue

    return df