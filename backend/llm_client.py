"""
llm_client.py
Provider-agnostic LLM client with intelligent contextual fallback.
Guarantees 100% demo reliability even without API keys.
"""
import os
import json
from config import settings

class LLMClient:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.gemini_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self.openai_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")

    def generate_chat_response(
        self,
        user_message: str,
        user_profile: dict,
        analysis_data: dict,
        knowledge_context: str,
        language: str = "en"
    ) -> str:
        """
        Generates grounded chat responses.
        Uses external LLM if configured; otherwise uses deterministic smart coach logic.
        """
        # If external API keys exist, try them first
        if self.gemini_key and (self.provider == "gemini" or self.provider == "auto"):
            try:
                import httpx
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
                prompt_text = f"""You are ArthMitra, an empathetic, certified Indian personal finance coach.
User Language: {language}
User Profile: {json.dumps(user_profile)}
Computed Financial Metrics: {json.dumps(analysis_data)}
Relevant Knowledge:
{knowledge_context}

RULES:
- Ground all numbers strictly in Computed Financial Metrics. Never invent figures.
- Refuse stock tips or market predictions politely.
- If language is 'hi', reply in clear conversational Hindi. If 'ta', reply in Tamil. If 'en', reply in English.
- User Question: {user_message}"""
                response = httpx.post(
                    url,
                    json={"contents": [{"parts": [{"text": prompt_text}]}]},
                    timeout=10.0
                )
                if response.status_code == 200:
                    cand = response.json().get("candidates", [])
                    if cand:
                        return cand[0]["content"]["parts"][0]["text"].strip()
            except Exception:
                pass # fallback below

        # Smart deterministic engine fallback
        return self._generate_grounded_fallback(user_message, user_profile, analysis_data, knowledge_context, language)

    def _generate_grounded_fallback(
        self,
        user_message: str,
        user_profile: dict,
        analysis_data: dict,
        knowledge_context: str,
        language: str = "en"
    ) -> str:
        q = user_message.lower()
        score_data = analysis_data.get("health_score", {})
        score = score_data.get("score", 0)
        band = score_data.get("band", "Fair")
        
        cashflow = analysis_data.get("cashflow", {})
        savings_cap = cashflow.get("savings_capacity", 0)
        savings_rate = cashflow.get("savings_rate", 0)
        
        debt = analysis_data.get("debt", {})
        dti = debt.get("dti_ratio", 0)
        pay_first = debt.get("pay_this_first")
        
        emergency = analysis_data.get("emergency", {})
        em_gap = emergency.get("gap", 0)
        em_months = emergency.get("months_covered", 0)
        
        # Check stock tips / market timing query
        if any(w in q for w in ["stock", "share", "crypto", "bitcoin", "penny", "multibagger", "tip", "buy or sell", "nifty target", "sensex target", "market prediction"]):
            if language == "hi":
                return (
                    "⚠️ **कृपया ध्यान दें**: सेबी (SEBI) के दिशानिर्देशों के अनुसार, मैं व्यक्तिगत स्टॉक टिप्स या बाजार की भविष्यवाणी नहीं करता।\n\n"
                    "एक अनुशासित निवेशक के लिए व्यक्तिगत शेयरों के पीछे भागने के बजाय **कम लागत वाले इंडेक्स फंड (जैसे Nifty 50)** में SIP करना अधिक सुरक्षित और लाभकारी होता है। "
                    "यह पूरे भारतीय विकास में निवेश करता है और व्यक्तिगत कंपनियों के जोखिम को समाप्त करता है।"
                )
            elif language == "ta":
                return (
                    "⚠️ **கவனிக்கவும்**: செபி (SEBI) வழிகாட்டுதலின்படி, நான் குறிப்பிட்ட பங்குகள் (stocks) அல்லது சந்தை கணிப்புகளை பரிந்துரைக்க மாட்டேன்.\n\n"
                    "தனிப்பட்ட பங்குகளை தேர்ந்தெடுப்பதை விட, **குறைந்த கட்டண இன்டெக்ஸ் ஃபண்டுகளில் (Nifty 50 Index)** மாதந்தோறும் SIP முதலீடு செய்வது உங்கள் பணத்திற்கு நீண்ட கால பாதுகாப்பு அளிக்கும்."
                )
            else:
                return (
                    "⚠️ **Compliance Notice**: As an educational financial coach, I do not provide individual stock tips or market predictions.\n\n"
                    "For disciplined wealth building, empirical research shows that broad-market **low-cost Index Funds (such as Nifty 50 / Nifty 500)** consistently outperform 80%+ of active stock pickers over a 10-year period. "
                    "This lets you participate in India's macroeconomic growth without single-company failure risk."
                )

        # Why is my score X?
        if any(w in q for w in ["score", "why is my score", "health score"]):
            sub_scores = score_data.get("sub_scores", [])
            reasons = "\n".join([f"• **{s['name']}** ({s['score']}/100): {s['reason']}" for s in sub_scores])
            if language == "hi":
                return (
                    f"🎯 आपका वित्तीय स्वास्थ्य स्कोर **{score}/100** ({band}) है।\n\n"
                    f"**स्कोर के मुख्य कारण:**\n{reasons}\n\n"
                    f"💡 **सुझाव**: स्कोर बढ़ाने के लिए सबसे पहले इमरजेंसी फंड का अंतर (₹{em_gap:,.0f}) भरें और उच्च ब्याज वाले कर्जों को चुकता करें।"
                )
            elif language == "ta":
                return (
                    f"🎯 உங்கள் நிதி ஆரோக்கிய மதிப்பீடு: **{score}/100** ({band}).\n\n"
                    f"**காரணங்கள்:**\n{reasons}\n\n"
                    f"💡 **அடுத்த நடவடிக்கை**: அவசரக்கால நிதியை (Emergency Fund) நிரப்புவது மற்றும் கடனை குறைப்பது உங்கள் மதிப்பெண்ணை உடனடியாக உயர்த்தும்."
                )
            else:
                return (
                    f"🎯 Your Financial Health Score is **{score}/100** (Rating: **{band}**).\n\n"
                    f"**Breakdown of your sub-scores:**\n{reasons}\n\n"
                    f"💡 **Primary Action**: Your fastest path to an 85+ score is closing your ₹{em_gap:,.0f} emergency cushion gap and systematically prepaying high-interest debt."
                )

        # Loan prepayment vs SIP
        if any(w in q for w in ["prepay", "loan or sip", "debt or invest", "prepayment"]):
            if pay_first and pay_first.get("interest_rate", 0) > 11.0:
                rec_text_en = (
                    f"Based on your profile, you hold **{pay_first['loan_name']}** at an interest rate of **{pay_first['interest_rate']}%**.\n\n"
                    f"👉 **Verdict: Prepay the loan first!**\n"
                    f"A guaranteed 42% or 12%+ interest expense saved through prepayment mathematically beats the uncertain ~12% equity market return. "
                    f"Prepaying saves you ₹{debt.get('avalanche_plan', {}).get('interest_saved_vs_baseline', 0):,.0f} in interest drag."
                )
                rec_text_hi = (
                    f"आपके पास **{pay_first['loan_name']}** है जिसकी ब्याज दर **{pay_first['interest_rate']}%** है।\n\n"
                    f"👉 **सिफारिश: पहले लोन चुकाएं!**\n"
                    f"लोन पर लगने वाले उच्च ब्याज को बचाना शेयर बाजार से मिलने वाले अनिश्चित रिटर्न से कहीं अधिक सुरक्षित और लाभदायक है।"
                )
                rec_text_ta = (
                    f"உங்கள் கடன் **{pay_first['loan_name']}**-ன் வட்டி விகிதம் **{pay_first['interest_rate']}%** ஆகும்.\n\n"
                    f"👉 **முடிவு: முதலீடு செய்வதற்கு முன் கடனை முன்கூட்டியே செலுத்துங்கள்!** அதிக வட்டி கடனை அடைப்பது உறுதியான லாபமாகும்."
                )
            else:
                rec_text_en = (
                    f"Your loans carry modest interest rates (under 9%). While maintaining regular EMIs, continuing your long-term SIPs makes sense because equity compounding (~12% p.a.) exceeds your borrowing cost."
                )
                rec_text_hi = "आपकी लोन ब्याज दर नियंत्रित है (9% से कम)। अपनी नियमित EMI के साथ SIP जारी रखना सही रणनीति है।"
                rec_text_ta = "உங்கள் கடன் வட்டி விகிதம் குறைவாக உள்ளது (9% க்கும் குறைவு). எனவே முறையான EMI உடன் SIP முதலீட்டை தொடரலாம்."

            if language == "hi":
                return rec_text_hi
            elif language == "ta":
                return rec_text_ta
            return rec_text_en

        # Can I afford a bike/car loan?
        if any(w in q for w in ["afford", "bike loan", "car loan", "buy a car", "new loan", "emi"]):
            if dti > 35.0 or savings_cap < 10000:
                en_ans = (
                    f"⚠️ **Affordability Analysis**: Currently, your Debt-to-Income ratio is already **{dti:.1f}%**, and your uncommitted monthly savings capacity is **₹{savings_cap:,.0f}**.\n\n"
                    f"Taking an additional vehicle loan EMI right now would push your DTI into the critical zone (>40%) and squeeze your ability to invest for emergency reserves. "
                    f"**Recommendation**: Postpone the purchase by 6-9 months until your current debts are trimmed or save a larger down payment in cash."
                )
                hi_ans = (
                    f"⚠️ **सामर्थ्य विश्लेषण**: वर्तमान में आपका कर्ज अनुपात (DTI) **{dti:.1f}%** है और मासिक बचत ₹{savings_cap:,.0f} है।\n\n"
                    f"नया लोन लेना आपके बजट पर अतिरिक्त दबाव डालेगा। सलाह: अगले 6-9 महीने रुकें और डाउनपेमेंट के लिए नकद बचत करें।"
                )
                ta_ans = (
                    f"⚠️ **கடன் வாங்கும் திறன்**: தற்போது உங்கள் கடன் சுமை {dti:.1f}% ஆக உள்ளது. புதிய பைக்/கார் கடன் வாங்குவது உங்கள் அவசரக்கால சேமிப்பை பாதிக்கும். சில மாதங்கள் தள்ளிப்போடுவது நல்லது."
                )
            else:
                en_ans = (
                    f"✅ **Affordability Analysis**: Your current DTI is healthy at **{dti:.1f}%** and your monthly surplus is **₹{savings_cap:,.0f}**.\n\n"
                    f"You can comfortably absorb an EMI up to ₹{savings_cap * 0.35:,.0f}/month without jeopardizing your emergency savings. "
                    f"Ensure you pay at least 20-30% as down payment to minimize total financing interest."
                )
                hi_ans = f"✅ आपका वित्तीय संतुलन मजबूत है (DTI: {dti:.1f}%)। आप ₹{savings_cap * 0.35:,.0f}/माह तक की EMI वहन कर सकते हैं।"
                ta_ans = f"✅ உங்கள் நிதி நிலை நன்றாக உள்ளது. நீங்கள் மாதம் ₹{savings_cap * 0.35:,.0f} வரை EMI செலுத்த தகுதி உடையவர்."

            if language == "hi":
                return hi_ans
            elif language == "ta":
                return ta_ans
            return en_ans

        # Emergency fund questions
        if any(w in q for w in ["emergency", "cushion", "liquid", "contingency"]):
            en_ans = (
                f"🛡️ **Emergency Fund Status**: You currently have **₹{emergency.get('current_amount', 0):,.0f}** parked, covering **{em_months:.1f} months** of essential expenses.\n\n"
                f"Your target is **{emergency.get('target_months', 6)} months (₹{emergency.get('target_amount', 0):,.0f})**.\n"
                f"Recommended allocation: **₹{emergency.get('recommended_monthly_allocation', 0):,.0f}/month**.\n\n"
                f"**Where to keep it:**\n"
                f"1. 30% in Instant Bank Savings (UPI / ATM ready)\n"
                f"2. 40% in Overnight / Liquid Mutual Fund\n"
                f"3. 30% in Auto-Sweep Bank Fixed Deposit"
            )
            hi_ans = (
                f"🛡️ **इमरजेंसी फंड स्थिति**: आपके पास अभी ₹{emergency.get('current_amount', 0):,.0f} हैं, जो {em_months:.1f} महीनों के खर्च को कवर करता है।\n"
                f"लक्ष्य: {emergency.get('target_months', 6)} महीने (₹{emergency.get('target_amount', 0):,.0f})।\n"
                f"इसे बैंक बचत खाते और लिक्विड म्यूचुअल फंड में सुरक्षित रखें।"
            )
            ta_ans = (
                f"🛡️ **அவசரகால நிதி**: உங்களிடம் தற்போது ₹{emergency.get('current_amount', 0):,.0f} உள்ளது ({em_months:.1f} மாதங்கள்). "
                f"இலக்கு: ₹{emergency.get('target_amount', 0):,.0f}. இதை சேமிப்பு வங்கி கணக்கு மற்றும் லிக்விட் ஃபண்டில் வைக்கவும்."
            )
            if language == "hi":
                return hi_ans
            elif language == "ta":
                return ta_ans
            return en_ans

        # Default general response grounded in user's numbers
        if language == "hi":
            return (
                f"नमस्ते! मैं आपका अर्थमित्र (ArthMitra) कोच हूँ।\n\n"
                f"आपकी वर्तमान स्थिति:\n"
                f"• मासिक आय: ₹{cashflow.get('monthly_income', 0):,.0f}\n"
                f"• बचत दर: {savings_rate:.1f}%\n"
                f"• स्वास्थ्य स्कोर: {score}/100\n\n"
                f"आप मुझसे इमरजेंसी फंड, लोन प्रीपेमेंट, SIP या अपने लक्ष्यों के बारे में कोई भी सवाल पूछ सकते हैं!"
            )
        elif language == "ta":
            return (
                f"வணக்கம்! நான் உங்கள் அர்த்தமித்ரா (ArthMitra) நிதி ஆலோசகர்.\n\n"
                f"உங்கள் நிதி சுருக்கம்:\n"
                f"• மாத வருமானம்: ₹{cashflow.get('monthly_income', 0):,.0f}\n"
                f"• சேமிப்பு விகிதம்: {savings_rate:.1f}%\n"
                f"• ஆரோக்கிய மதிப்பீடு: {score}/100\n\n"
                f"SIP முதலீடு, கடன் திருப்பிச் செலுத்துதல், அவசரக்கால நிதி குறித்து நீங்கள் கேட்கலாம்."
            )
        else:
            return (
                f"Hello! I am ArthMitra, your personal finance coach.\n\n"
                f"**Your Snapshot**:\n"
                f"• Monthly Income: ₹{cashflow.get('monthly_income', 0):,.0f}\n"
                f"• Savings Rate: {savings_rate:.1f}% (Surplus: ₹{savings_cap:,.0f}/mo)\n"
                f"• Debt-to-Income (DTI): {dti:.1f}%\n"
                f"• Financial Health Score: **{score}/100** ({band})\n\n"
                f"Feel free to ask me questions like *'Why is my score {score}?'*, *'Should I prepay my loan or start an SIP?'*, or *'How can I save more each month?'*."
            )

llm_client = LLMClient()
