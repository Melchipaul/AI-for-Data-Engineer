from openai import OpenAI
import pandas as pd
import sqlite3
import json


from flask import Flask, render_template, request

app = Flask(__name__)


# Set up OpenAI API key
client = OpenAI(api_key='')

def clean(dict_variable):
    return next(iter(dict_variable.values()))

def create_query(question):

    schema = """

    customer (
        customer_id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT,
        join_date TEXT
    )

    sales (
        sale_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        product TEXT,
        amount REAL,
        sale_date TEXT,
        FOREIGN KEY(customer_id) REFERENCES customer(customer_id)
    )

    """

    prompt = f""" Given the following schema, create SQLlite3 query that will get us the answer. 
    Output the query in JSON

    Schema:
    {schema}

    Question:
    {question}

    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    return clean(json.loads(response.choices[0].message.content))


def run_query(query):

    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    cursor.execute(query)
    output = '{}'.format(cursor.fetchall())
    conn.close()

    return output


def interpret_results(question, results):

    prompt = f"""Given the following results outputted from a database based on the user's question,
    answer the user's question concisely
    
    Results:
    {results}

    User's question
    {question}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


# example run
def get_question_and_return_answer(question):

    query = create_query(question)
    print('Query')
    print(query)
    print('---')

    results = run_query(query)
    print('Results')
    print(results)
    print('---')

    answer = interpret_results(question, results)

    print(answer)

    return answer


@app.route('/', methods=['GET', 'POST'])
def index():
    result = ""
    if request.method == 'POST':
        question = request.form['text']
        result = get_question_and_return_answer(question)
    return render_template('index.html', result=result)

if __name__ == '__main__':
    app.run(debug=True)






