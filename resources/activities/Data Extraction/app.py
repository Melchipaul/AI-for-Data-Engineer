import pandas as pd
import json
from openai import OpenAI
import os

# Set up OpenAI API key
client = OpenAI(api_key='')

def clean(dict_variable):
    return next(iter(dict_variable.values()))

text_list = []
for filename in os.listdir('contracts'):
    file_path = os.path.join('contracts', filename)
    with open(file_path, 'r', encoding='utf-8') as file:
         text = file.read()
         text_list.append(text)

def get_features(text):

    prompt = f"""Given this contract text, extract the following fields: 'Employee Name', 
    'Yearly Salary', 'Non-Compete Clause (Y/N)', 'Start Date'. Output in the following JSON format
    "Agreement": "Employee Name": "..." 
    
    Contract text:
    {text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={'type': 'json_object'}
    )

    return clean(json.loads(response.choices[0].message.content))

output_list = []

for t in text_list:
    output_list.append(get_features(t))

output_df = pd.DataFrame(output_list)
output_df.to_csv('extracted_features.csv', index=False)
