"""
Simple web UI for the brief validator.
"""

from flask import Flask, render_template, request, jsonify
from brief_validator_agent import validate_brief

app = Flask(__name__)

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/validate', methods=['POST'])
def validate():
    """Validate the brief text and return results."""
    brief_text = request.json.get('brief_text', '')
    if not brief_text:
        return jsonify({
            'error': 'No brief text provided'
        }), 400
    
    # Validate the brief
    result = validate_brief(brief_text)
    
    return jsonify({
        'result': result
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001) 