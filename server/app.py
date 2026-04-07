from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import pickle
from pathlib import Path

app = Flask(__name__)
# Enable CORS so WordPress can communicate with this API on localhost
CORS(app)

# Point to the trained model from the Training folder
MODEL_PATH = Path(__file__).parent.parent / "Training" / "xgboost_deal_model.pkl"

print("Loading model into memory...")
try:
    with open(MODEL_PATH, "rb") as f:
        bundle = pickle.load(f)
    model = bundle["model"]
    feature_columns = bundle["feature_columns"]
    print("Model loaded and ready!")
except FileNotFoundError:
    print(f"Error: Model not found at {MODEL_PATH}")
    model = None
    feature_columns = []

@app.route('/predict', methods=['POST'])
def predict():
    if model is None:
        return jsonify({"success": False, "error": "Model not loaded"}), 500
        
    try:
        # Get the JSON property data from WordPress
        data = request.json
        
        # Convert to Pandas DataFrame
        df = pd.DataFrame([data])
        
        # Ensure all required features are present, fill with 0 if missing
        for col in feature_columns:
            if col not in df.columns:
                df[col] = 0
                
        # Reorder columns to exactly match what the model expects
        df = df[feature_columns]

        # Make the prediction
        pred = model.predict(df)[0]
        
        # Return the float price
        return jsonify({
            "success": True, 
            "predicted_price": float(pred)
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

if __name__ == '__main__':
    # Run the server on port 5000
    app.run(port=5000, debug=True)
