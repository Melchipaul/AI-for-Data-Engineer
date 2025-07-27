from flask import Flask, render_template, request, send_file
import pandas as pd
import io
import json
from openai import OpenAI

# Set up OpenAI API key
client = OpenAI(api_key='')

def clean(dict_variable):
    return next(iter(dict_variable.values()))

app = Flask(__name__)


def create_sample_rows(df, rows=10):

    prompt = f"""Given this product data: {df.to_dict('records')}, 
    generate {rows} additional records in the same format, 
    maintaining similar patterns but with different values. 
    Output in JSON form."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    new_rows = pd.DataFrame(clean(json.loads(response.choices[0].message.content)))

    return pd.concat([df, new_rows])

@app.route('/', methods=['GET', 'POST'])
def index():

    if request.method == 'POST':
        # Check if a file was uploaded
        if 'file' not in request.files:
            return 'No file uploaded', 400
        
        file = request.files['file']
        number_of_rows = int(request.form.get('number_of_rows', 10))
        
        # Check if the file has a name
        if file.filename == '':
            return 'No file selected', 400
        
        if file and file.filename.endswith('.csv'):

            df = pd.read_csv(file)
            df_augmented = create_sample_rows(df, number_of_rows)

            output = io.BytesIO()
            df_augmented.to_csv(output, index=False)
            output.seek(0)

            return send_file(
                output,
                as_attachment=True,
                download_name='augmented' + file.filename,
                mimetype='text/csv'
            )
        
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
