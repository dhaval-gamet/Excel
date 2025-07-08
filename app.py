from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import json # JSON मॉड्यूल इम्पोर्ट करें
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv() # .env फ़ाइल से एन्वायरमेंट वेरिएबल्स लोड करें
CORS(app) # CORS इनेबल करें ताकि फ्रंटएंड से रिक्वेस्ट आ सके

# अपनी Groq API कुंजी यहां सेट करें
API_KEY = os.getenv("GROQ_API_KEY")

@app.route("/", methods=["GET"])
def home():
    """बेसिक होम रूट यह जांचने के लिए कि API चल रहा है या नहीं।"""
    return "🧠 Groq Chatbot API is running!"

@app.route("/chat", methods=["POST"])
def chat():
    """
    यूजर के नेचुरल लैंग्वेज कमांड को प्रोसेस करता है और Groq API का उपयोग करके
    उन्हें एक्सेल एक्शन्स में बदलता है।
    """
    data = request.json
    
    # फ्रंटएंड से 'message' (यूजर कमांड) और 'excelData' प्राप्त करें
    user_msg = data.get("message", "") 
    excel_data = data.get("excelData", {}) 

    if not user_msg:
        return jsonify({"error": "No message provided"}), 400

    # AI को दिए जाने वाले सिस्टम प्रॉम्प्ट को और विस्तृत करें
    # उसे बताएं कि वह एक्सेल ऑपरेशन कर सकता है और JSON फॉर्मेट में कैसे जवाब दे
    system_prompt = """
    आप एक बहुत ही बुद्धिमान और कुशल एक्सेल सहायक हैं। आपका काम उपयोगकर्ता के हिंदी में दिए गए कमांड्स को समझना और उन्हें JSON फॉर्मेट में एक्सेल एक्शन्स में बदलना है।
    उपयोगकर्ता ने आपको वर्तमान एक्सेल ग्रिड का डेटा भी प्रदान किया है, जिसका उपयोग आप गणना या संदर्भ के लिए कर सकते हैं।

    आपके जवाब में एक 'actions' नाम की JSON लिस्ट होनी चाहिए। हर एक्शन ऑब्जेक्ट में 'action' का प्रकार (जैसे 'sum', 'average', 'write', 'highlight', 'sort', 'filter') और उस एक्शन के लिए आवश्यक पैरामीटर्स होने चाहिए।

    समर्थित एक्शन प्रकार और उनके अपेक्षित पैरामीटर्स:
    1.  **sum**: रेंज में संख्याओं का योग करता है।
        -   `action`: "sum"
        -   `range`: स्ट्रिंग (जैसे "A1:A10")
        -   `target`: स्ट्रिंग (वह सेल जहाँ परिणाम लिखना है, जैसे "A11")
        उदाहरण:
        यूजर: "A1 से A5 जोड़ो और A6 में लिखो"
        आपका JSON: `{"actions": [{"action": "sum", "range": "A1:A5", "target": "A6"}]}`

    2.  **average**: रेंज में संख्याओं का औसत निकालता है।
        -   `action`: "average"
        -   `range`: स्ट्रिंग (जैसे "B1:B10")
        -   `target`: स्ट्रिंग (वह सेल जहाँ परिणाम लिखना है, जैसे "B11")
        उदाहरण:
        यूजर: "B1 से B5 का औसत निकालो और B6 में लिखो"
        आपका JSON: `{"actions": [{"action": "average", "range": "B1:B5", "target": "B6"}]}`

    3.  **write**: किसी विशिष्ट सेल में एक मान लिखता है।
        -   `action`: "write"
        -   `target`: स्ट्रिंग (वह सेल जहाँ लिखना है, जैसे "C1")
        -   `value`: कोई भी मान (स्ट्रिंग, संख्या) जिसे लिखना है।
        उदाहरण:
        यूजर: "D2 में 'मेरा डेटा' लिखो"
        आपका JSON: `{"actions": [{"action": "write", "target": "D2", "value": "मेरा डेटा"}]}`
        यूजर: "E3 में 123 लिखो"
        आपका JSON: `{"actions": [{"action": "write", "target": "E3", "value": 123}]}`

    4.  **highlight**: एक या अधिक सेल्स को हाइलाइट करता है।
        -   `action`: "highlight"
        -   `range`: स्ट्रिंग (जैसे "A1" या "A1:C5")
        -   `color`: स्ट्रिंग (CSS रंग का नाम या हेक्स कोड, जैसे "yellow", "#FFFF00", "lightgreen")
        उदाहरण:
        यूजर: "F1 से G5 तक पीला करो"
        आपका JSON: `{"actions": [{"action": "highlight", "range": "F1:G5", "color": "yellow"}]}`

    5.  **sort**: किसी कॉलम को सॉर्ट करता है।
        -   `action`: "sort"
        -   `column`: स्ट्रिंग (कॉलम का नाम, जैसे "A")
        -   `order`: स्ट्रिंग ("asc" (आरोही) या "desc" (अवरोही))
        उदाहरण:
        यूजर: "कॉलम A को आरोही क्रम में सॉर्ट करो"
        आपका JSON: `{"actions": [{"action": "sort", "column": "A", "order": "asc"}]}`

    6.  **filter**: किसी कॉलम को फिल्टर करता है।
        -   `action`: "filter"
        -   `column`: स्ट्रिंग (कॉलम का नाम, जैसे "A")
        -   `value`: स्ट्रिंग या संख्या (जिस मान पर फ़िल्टर करना है)
        उदाहरण:
        यूजर: "कॉलम B में 'पूर्ण' वाले को फ़िल्टर करो"
        आपका JSON: `{"actions": [{"action": "filter", "column": "B", "value": "पूर्ण"}]}`


    महत्वपूर्ण बातें:
    -   हमेशा वैध JSON आउटपुट दें। कोई अतिरिक्त टेक्स्ट या मार्किंग नहीं।
    -   यदि कमांड में कई एक्शन्स हैं, तो 'actions' लिस्ट में सभी एक्शन्स को शामिल करें।
    -   यदि उपयोगकर्ता का कमांड किसी एक्सेल एक्शन से मेल नहीं खाता है, तो केवल एक सामान्य, सहायक टेक्स्ट `reply` (स्ट्रिंग) प्रदान करें। इस स्थिति में 'actions' लिस्ट खाली होगी या मौजूद नहीं होगी।
    -   जवाब देते समय, एक्सेल डेटा (जो आपको दिया गया है) को सीधे दोहराएं नहीं। उसका उपयोग केवल संदर्भ के लिए करें।
    अब यूजर का कमांड प्रोसेस करें।
    """

    # यूजर का मैसेज और एक्सेल डेटा दोनों Groq को भेजें
    # excelData को JSON स्ट्रिंग के रूप में भेजें ताकि AI उसे पढ़ सके
    full_user_message = f"User Command: {user_msg}\n\nCurrent Excel Data:\n{json.dumps(excel_data, indent=2)}"

    api_payload = {
        "model": "llama3-8b-8192", # आप यहां एक और शक्तिशाली मॉडल का उपयोग कर सकते हैं यदि उपलब्ध हो
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_user_message}
        ],
        "temperature": 0.0 # AI को अधिक सटीक और कम रचनात्मक बनाने के लिए
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=api_payload,
            timeout=20 # API टाइमआउट बढ़ाएं
        )
        res.raise_for_status() # HTTP त्रुटियों के लिए अपवाद उठाएं
        
        # Groq से मिला पूरा JSON रिस्पांस लें
        groq_response_content = res.json()["choices"][0]["message"]["content"]
        
        # AI के जवाब को JSON के रूप में पार्स करने की कोशिश करें
        try:
            parsed_response = json.loads(groq_response_content)
            # अगर 'actions' की कुंजी है, तो उस ऑब्जेक्ट को भेजें
            if "actions" in parsed_response and isinstance(parsed_response["actions"], list):
                return jsonify(parsed_response)
            else:
                # अगर AI ने JSON दिया लेकिन उसमें वैध 'actions' लिस्ट नहीं है
                return jsonify({"reply": groq_response_content})
        except json.JSONDecodeError:
            # अगर AI ने JSON के अलावा कुछ और दिया
            return jsonify({"reply": groq_response_content})

    except requests.exceptions.Timeout:
        return jsonify({"error": "Groq API timeout", "message": "The AI took too long to respond."}), 504
    except requests.exceptions.RequestException as e:
        # Groq API से संबंधित अन्य HTTP त्रुटियां
        return jsonify({"error": "Groq API request failed", "details": str(e)}), 500
    except Exception as e:
        # कोई अन्य अप्रत्याशित त्रुटि
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

if __name__ == '__main__':
    # Python एप्लिकेशन को चलाएं
    # होस्ट को '0.0.0.0' पर सेट करने से यह लोकल नेटवर्क में एक्सेसिबल हो जाता है
    # पोर्ट 10000 पर चल रहा है
    app.run(host="0.0.0.0", port=10000, debug=True) # debug=True विकास के लिए उपयोगी है
