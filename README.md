# Meeting Summary App

This is a **Streamlit-based application** that transcribes and summarizes meeting recordings using **Whisper** for speech-to-text and **Gemini AI** for text summarization.

---

## 🚀 Features
- 🎧 **Transcribes audio recordings** (MP3, WAV, M4A) using Whisper.
- 📝 **Summarizes meeting transcripts** using Google Gemini AI.
- 🔑 **Supports API key input** for Gemini.
- 🎯 **Simple UI** built with Streamlit.

---

## 🛠️ Installation & Setup

### **1️⃣ Clone the Repository**
```bash
git clone https://github.com/mokshupadhyay/Meeting-Summary-App.git
cd Meeting-Summary-App
```

### **2️⃣ Create & Activate Virtual Environment**
#### **On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```
#### **On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### **3️⃣ Install Dependencies**
```bash
pip install -r requirements.txt
```

---

## 🔑 API Key Setup

1. Get your **Google Gemini API Key** from [Google AI Studio](https://ai.google.dev/).
2. Enter the API key when prompted in the Streamlit app.

---

## ▶️ Run the Application

```bash
streamlit run meetsummary.py
```

- Open the **local URL** in your browser (e.g., `http://localhost:8501`).
- Upload an **audio file** or **text transcript** to generate a summary.

---

## ⚡ Example Usage
1. **Upload an audio file** (`.mp3`, `.wav`, `.m4a`).
2. **Wait for transcription** (Whisper will process the audio).
3. **Gemini AI generates a summary** of the meeting.
4. **View and copy** the summary for your records.

---

## 🤖 Dependencies
- **Python 3.8+**
- **Streamlit**
- **OpenAI Whisper**
- **Google Gemini AI SDK**

---

## 🛠️ Troubleshooting
### **❌ Getting `Error: No available Gemini model found`?**
- Check your API key at [Google AI Console](https://ai.google.dev/).
- Ensure your API key is **entered correctly** in the Streamlit UI.

### **❌ Can't install dependencies?**
- Run:
  ```bash
  pip install --upgrade pip
  pip install -r requirements.txt
  ```

---

## 📝 License
This project is open-source and free to use. Contributions are welcome!

---

### **👨‍💻 Created by Moksh Upadhyay**

