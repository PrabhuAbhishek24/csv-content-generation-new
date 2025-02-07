from flask import Flask, request, jsonify, send_file
import openai
import os
import zipfile
import io
import csv
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Function to get response from OpenAI using chat completions
def get_response(text):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": text}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# Function to fetch medical and pharma-related data
def fetch_medical_pharma_data(query):
    prompt = f"""
    Please provide reliable and accurate medical and pharmaceutical data related to the following query.
    The data should include at least 15 to 20 entries and be formatted as a CSV for the medical and pharmaceutical domain only.
    The data must be accurate and trustworthy.

    Query: {query}

    The result should be in CSV format with headers and rows.
    """
    response = get_response(prompt)
    return response



def create_scorm_package(csv_content):
    # Create an in-memory binary stream for the zip file
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        # Add the CSV content to the zip file
        zip_file.writestr("generated_data.csv", csv_content)

        # Add imsmanifest.xml to the zip file
        imsmanifest_content = """<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="scorm_2004" version="1.0">
    <organizations>
        <organization identifier="org_1">
            <title>CSV SCORM Package</title>
        </organization>
    </organizations>
    <resources>
        <resource identifier="res_1" type="webcontent" href="index.html">
            <file href="generated_data.csv"/>
            <file href="index.html"/>
        </resource>
    </resources>
</manifest>"""
        zip_file.writestr("imsmanifest.xml", imsmanifest_content)

        # Add index.html to the zip file
        index_html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>CSV Content</title>
</head>
<body>
    <h1>Generated CSV Content</h1>
    <p>This package contains the CSV data you requested: {}</p>
</body>
</html>
""".format(csv_content.replace('\n', '<br>'))
        zip_file.writestr("index.html", index_html_content)

    # Rewind the buffer to the beginning
    zip_buffer.seek(0)
    return zip_buffer


# API endpoint to generate CSV data
@app.route('/generate-csv', methods=['POST'])
def generate_csv():
    try:
        data = request.get_json()
        query = data.get("query", "").strip()

        if not query:
            return jsonify({"error": "Query is required."}), 400

        gpt_response = fetch_medical_pharma_data(query)

        csv_output = io.StringIO()
        writer = csv.writer(csv_output)
        for row in gpt_response.split("\n"):
            writer.writerow(row.split(","))

        return jsonify({"csv_content": csv_output.getvalue()})
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

# API endpoint to download SCORM package
@app.route('/download-scorm', methods=['POST'])
def download_scorm():
    try:
        data = request.get_json()
        csv_content = data.get("csv_content", "")

        if not csv_content:
            return jsonify({"error": "CSV content is required."}), 400

        scorm_package = create_scorm_package(csv_content)

        return send_file(
            scorm_package,
            as_attachment=True,
            download_name="csv_scorm_package.zip",
            mimetype="application/zip"
        )
    except Exception as e:
        return jsonify({"error": f"Error in generating SCORM package: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
