from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import random
import hashlib
import json

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agro_vision.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class PredictionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prediction_type = db.Column(db.String(50), nullable=False) # 'crop', 'yield', 'fertilizer', 'disease'
    input_data = db.Column(db.String(500), nullable=True) # stringified json inputs
    result = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

with app.app_context():
    db.create_all()

def safe_int(val, default=0):
    """Safely convert to int, returning default for empty/invalid values."""
    if val is None or val == '':
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def safe_float(val, default=0.0):
    """Safely convert to float, returning default for empty/invalid values."""
    if val is None or val == '':
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

@app.route('/')
def home():
    return "Agro-AI Backend is Running! Please use the standalone HTML file to access the UI."

# --- Mock AI Logic (To be replaced with real models if available) ---

def recommend_crop(data):
    """Expanded crop recommendation with strong South Indian crop support."""
    n = safe_int(data.get('n'), 50)
    p = safe_int(data.get('p'), 50)
    k = safe_int(data.get('k'), 50)
    ph = safe_float(data.get('ph'), 6.5)
    temp = safe_float(data.get('temp'), 28)
    humidity = safe_float(data.get('humidity'), 70)
    rainfall = safe_float(data.get('rainfall'), 100)
    season = data.get('season') or 'Kharif'
    soil_type = (data.get('soil_type') or 'Loamy').lower()

    crop = "Coconut (Thennai)"
    if season == 'Kharif':
        if rainfall > 200 and temp > 25:
            crop = "Paddy (Rice)"
        elif rainfall > 150 and humidity > 70:
            crop = "Sugarcane"
        elif n > 60 and p > 40:
            crop = "Maize"
        elif rainfall < 100 and soil_type == 'sandy':
            crop = "Bajra"
        else:
            crop = "Jowar"
    elif season == 'Rabi':
        if temp < 25 and humidity < 60:
            crop = "Wheat"
        elif k > 30 and temp < 22:
            crop = "Chickpea"
        elif temp < 25:
            crop = "Mustard"
        else:
            crop = "Barley"
    elif season == 'Zaid':
        if temp > 30:
            crop = "Watermelon"
        else:
            crop = "Cucumber"

    return crop


def predict_yield(data):
    """Predict yield based on crop type, area, and irrigation."""
    area = safe_float(data.get('area'), 1)
    water = data.get('irrigation') or 'No'
    soil_type = (data.get('soil_type') or 'Loamy').lower()
    rainfall = safe_float(data.get('rainfall'), 100)

    # Base yield per acre in Tons
    base_yield_per_acre = 1.8
    
    if water == 'Yes':
        base_yield_per_acre *= 1.4
    if 'loamy' in soil_type:
        base_yield_per_acre *= 1.1
    if rainfall > 120:
        base_yield_per_acre *= 1.15

    total_yield = area * base_yield_per_acre
    return f"{round(total_yield, 2)} Tons"


def recommend_fertilizer(data):
    """Recommend fertilizer and calculate amounts based on area."""
    n = safe_int(data.get('n'), 50)
    p = safe_int(data.get('p'), 50)
    k = safe_int(data.get('k'), 50)
    area = safe_float(data.get('area'), 1)

    recommendations = []
    amounts = []

    # Simple logic for urea (N), DAP (P), MOP (K) requirements
    # Assumption: Standard target is 100-50-50 per hectare (~40-20-20 per acre)
    n_target = 40
    p_target = 20
    k_target = 20

    if n < n_target:
        needed = (n_target - n) * 2 * area # Rough conversion: 1 unit N deficiency needs ~2kg Urea/acre
        recommendations.append("Urea (Nitrogen)")
        amounts.append(f"{round(needed, 1)} kg Urea")
    
    if p < p_target:
        needed = (p_target - p) * 2.2 * area # 1 unit P needs ~2.2kg DAP
        recommendations.append("DAP (Phosphorus)")
        amounts.append(f"{round(needed, 1)} kg DAP")

    if k < k_target:
        needed = (k_target - k) * 1.6 * area # 1 unit K needs ~1.6kg MOP
        recommendations.append("MOP (Potash)")
        amounts.append(f"{round(needed, 1)} kg MOP")

    if not recommendations:
        return "Balanced NPK 19-19-19 (approx. 50kg/acre)"

    return f"{' + '.join(recommendations)} (Total: {', '.join(amounts)})"



def detect_disease(file_info):
    """
    Simulate disease detection. Uses file metadata (name + size) to produce
    varied but deterministic results per image, so the same image always gets
    the same diagnosis but different images get different diagnoses.
    """
    diseases = {
        "Leaf Blast (Pyricularia oryzae)": {
            "severity": "High",
            "cause": "Caused by the fungus Pyricularia oryzae. Spreads rapidly in humid conditions (>90% humidity), prolonged leaf wetness, excessive nitrogen fertilization, and temperatures between 25-30°C.",
            "cure": "Apply Tricyclazole 75 WP @ 0.6g/L or Isoprothiolane 40 EC. Remove and burn infected leaves. Ensure proper spacing between plants.",
            "crops": "Rice, Ragi"
        },
        "Brown Spot (Bipolaris oryzae)": {
            "severity": "Medium",
            "cause": "Caused by the fungus Bipolaris oryzae. Occurs due to nutrient deficiency (especially potassium), poor soil fertility, water stress, and seed-borne infection. Common in poorly maintained fields.",
            "cure": "Spray Mancozeb 75 WP @ 2.5g/L or Zineb 75 WP. Use potassium-rich fertilizers. Apply foliar spray of KCl at 1%.",
            "crops": "Rice"
        },
        "Bacterial Leaf Blight (Xanthomonas oryzae)": {
            "severity": "High",
            "cause": "Caused by the bacterium Xanthomonas oryzae. Spreads through irrigation water, wind-driven rain, and infected seeds. Worsened by excessive nitrogen use, waterlogging, and warm humid weather.",
            "cure": "Apply Streptocycline 0.5g + Copper Oxychloride 2.5g per liter. Drain excess water from fields. Avoid excess nitrogen.",
            "crops": "Rice"
        },
        "Late Blight (Phytophthora infestans)": {
            "severity": "High",
            "cause": "Caused by the oomycete Phytophthora infestans. Thrives in cool, wet conditions (15-22°C) with high humidity. Spreads rapidly through wind-borne spores during rainy/foggy weather.",
            "cure": "Spray Metalaxyl + Mancozeb (Ridomil Gold) @ 2.5g/L. Remove infected plant parts. Avoid overhead irrigation.",
            "crops": "Tomato, Potato"
        },
        "Early Blight (Alternaria solani)": {
            "severity": "Medium",
            "cause": "Caused by the fungus Alternaria solani. Occurs in warm, humid conditions with alternating wet and dry periods. Poor crop rotation, overcrowding, and infected plant debris are major contributors.",
            "cure": "Apply Chlorothalonil 75 WP @ 2g/L or Mancozeb. Rotate crops and remove plant debris after harvest.",
            "crops": "Tomato, Potato"
        },
        "Powdery Mildew": {
            "severity": "Medium",
            "cause": "Caused by various fungal species (Erysiphales). Favoured by warm days (20-30°C), cool nights, low rainfall, high humidity, and poor air circulation. Shaded and overcrowded areas are most susceptible.",
            "cure": "Spray Sulphur 80 WP @ 3g/L or Karathane 48 EC @ 1ml/L. Ensure good air circulation between plants.",
            "crops": "Mango, Grapes, Chili"
        },
        "Downy Mildew": {
            "severity": "High",
            "cause": "Caused by oomycete pathogens (Plasmopara, Peronospora). Thrives in cool, moist conditions with temperatures of 15-20°C and prolonged leaf wetness. Spread by wind and water splashes.",
            "cure": "Apply Metalaxyl + Mancozeb @ 2g/L. Remove and destroy infected leaves. Avoid waterlogging.",
            "crops": "Grapes, Cucurbits, Bajra"
        },
        "Anthracnose (Colletotrichum)": {
            "severity": "Medium",
            "cause": "Caused by the fungus Colletotrichum species. Occurs during warm, rainy weather (25-30°C). Spread through infected seeds, rain splashes, and contaminated tools. Wounds on fruits accelerate infection.",
            "cure": "Spray Carbendazim 50 WP @ 1g/L or Copper Oxychloride @ 3g/L. Prune affected branches and ensure drainage.",
            "crops": "Mango, Chili, Banana"
        },
        "Wilt Disease (Fusarium oxysporum)": {
            "severity": "High",
            "cause": "Caused by the soil-borne fungus Fusarium oxysporum. Enters through roots and blocks water-conducting vessels. Favoured by warm temperatures (25-30°C), acidic soil, waterlogging, and continuous monocropping.",
            "cure": "Drench soil with Carbendazim 2g/L. Use resistant varieties. Practice crop rotation with non-host crops.",
            "crops": "Banana, Tomato, Cotton"
        },
        "Mosaic Virus (TMV / CMV)": {
            "severity": "High",
            "cause": "Caused by Tobacco Mosaic Virus or Cucumber Mosaic Virus. Transmitted by aphids, whiteflies, and contaminated tools/hands. Infected seeds and mechanical damage also spread the virus.",
            "cure": "No chemical cure. Remove infected plants immediately. Control aphid vectors with Imidacloprid. Use virus-free seeds.",
            "crops": "Tapioca, Tobacco, Tomato"
        },
        "Rust (Puccinia spp.)": {
            "severity": "Medium",
            "cause": "Caused by Puccinia fungal species. Favoured by cool to warm temperatures (15-25°C), high humidity, heavy dew, and overcrowded planting. Spores spread easily through wind over long distances.",
            "cure": "Spray Propiconazole 25 EC @ 1ml/L or Mancozeb 75 WP. Use rust-resistant seed varieties.",
            "crops": "Wheat, Groundnut, Coffee"
        },
        "Cercospora Leaf Spot": {
            "severity": "Low",
            "cause": "Caused by Cercospora fungi. Develops in warm, humid conditions with frequent rainfall. Poor plant spacing, overhead irrigation, and lack of crop rotation increase susceptibility.",
            "cure": "Apply Carbendazim 50 WP @ 1g/L. Maintain proper plant spacing. Remove infected lower leaves.",
            "crops": "Groundnut, Beetroot, Sesame"
        },
        "Root Rot (Rhizoctonia solani)": {
            "severity": "High",
            "cause": "Caused by the soil-borne fungus Rhizoctonia solani. Thrives in poorly drained, waterlogged soils with high organic matter. Heavy rainfall, compacted soil, and infected planting material are key triggers.",
            "cure": "Treat seeds with Trichoderma viride @ 4g/kg. Drench soil with Copper Oxychloride. Improve drainage.",
            "crops": "Black Pepper, Coconut, Cardamom"
        },
        "Quick Wilt / Foot Rot (Phytophthora capsici)": {
            "severity": "High",
            "cause": "Caused by the oomycete Phytophthora capsici. Triggered by waterlogging, poor drainage, and heavy monsoon rains. The pathogen persists in soil and spreads through contaminated water and tools.",
            "cure": "Drench with Metalaxyl + Mancozeb (Ridomil Gold) @ 2g/L. Improve drainage. Apply Trichoderma to soil.",
            "crops": "Black Pepper, Betel Vine"
        },
        "Leaf Curl Virus": {
            "severity": "Medium",
            "cause": "Caused by Begomovirus transmitted by whiteflies (Bemisia tabaci). High whitefly populations during hot, dry weather increase infection rates. Continuous cropping and lack of vector control worsen spread.",
            "cure": "Control whitefly vectors with Thiamethoxam 25 WG @ 0.3g/L. Uproot severely infected plants. Use tolerant varieties.",
            "crops": "Chili, Tomato, Cotton"
        },
        "Healthy Leaf ✅": {
            "severity": "None",
            "cause": "No disease-causing factors detected. The leaf appears to be in good health with no signs of fungal, bacterial, or viral infection.",
            "cure": "No disease detected! Your crop looks healthy. Continue regular monitoring and balanced fertilization.",
            "crops": "All"
        }
    }

    disease_names = list(diseases.keys())

    # Use file metadata to create a deterministic but varied selection
    if file_info:
        filename = file_info.get('filename', '')
        filesize = file_info.get('filesize', 0)
        # Create a hash from filename + size so same image → same result,
        # but different images → different results
        hash_input = f"{filename}_{filesize}"
        hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        idx = hash_val % len(disease_names)
    else:
        idx = random.randint(0, len(disease_names) - 1)

    detected = disease_names[idx]
    info = diseases[detected]

    return {
        "disease": detected,
        "severity": info["severity"],
        "cause": info["cause"],
        "recommendation": info["cure"],
        "affected_crops": info["crops"]
    }


# --- Routes ---

@app.route('/api/predict-crop', methods=['POST'])
def handle_crop():
    data = request.json
    crop_name = recommend_crop(data)
    
    new_log = PredictionLog(prediction_type='crop', input_data=json.dumps(data), result=crop_name)
    db.session.add(new_log)
    db.session.commit()
    
    return jsonify({"prediction": crop_name})

@app.route('/api/predict-yield', methods=['POST'])
def handle_yield():
    data = request.json
    yield_val = predict_yield(data)
    
    new_log = PredictionLog(prediction_type='yield', input_data=json.dumps(data), result=yield_val)
    db.session.add(new_log)
    db.session.commit()
    
    return jsonify({"prediction": yield_val})

@app.route('/api/predict-fertilizer', methods=['POST'])
def handle_fertilizer():
    data = request.json
    fertilizer_val = recommend_fertilizer(data)
    
    new_log = PredictionLog(prediction_type='fertilizer', input_data=json.dumps(data), result=fertilizer_val)
    db.session.add(new_log)
    db.session.commit()
    
    return jsonify({"prediction": fertilizer_val})

@app.route('/api/detect-disease', methods=['POST'])
def handle_disease():
    file_info = None
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            # Read file size for hashing (varied detection)
            file_data = file.read()
            file_info = {
                'filename': file.filename,
                'filesize': len(file_data)
            }
            print(f"Received file: {file.filename} ({len(file_data)} bytes)")

    result = detect_disease(file_info)
    
    disease = result.get('disease', 'Unknown')
    new_log = PredictionLog(
        prediction_type='disease', 
        input_data=json.dumps(file_info) if file_info else 'No image data', 
        result=disease
    )
    db.session.add(new_log)
    db.session.commit()
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
