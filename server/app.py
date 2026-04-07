from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import pickle
from pathlib import Path

app = Flask(__name__)
# allow requests from the WP site (local dev)
CORS(app)

# path to the saved model bundle
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
        # get the property data from the website
        data = request.json
        
        # make it a 1-row dataframe
        df = pd.DataFrame([data])
        
        # fill missing features with 0 (so the pipeline still works)
        for col in feature_columns:
            if col not in df.columns:
                df[col] = 0
                
        # keep the same column order the model was trained with
        df = df[feature_columns]

        # predict
        pred = model.predict(df)[0]
        
        # send back the number
        return jsonify({
            "success": True, 
            "predicted_price": float(pred)
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

if __name__ == '__main__':
    # start the server
    app.run(port=5000, debug=True)
