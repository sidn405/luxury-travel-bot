# Flight Scraper Integration - Quick Setup Guide

## 📋 Prerequisites
✅ Aviapages API token (you already have this)
✅ Villers Jets affiliate ID
✅ Existing Luxury_Travel_Bot.py deployed on Railway

---

## 🚀 Quick Setup (5 minutes)

### 1. Add Flight Scraper to Your Project

Upload `flight_scraper.py` to the same directory as `Luxury_Travel_Bot.py`

```
your-project/
├── Luxury_Travel_Bot.py
├── flight_scraper.py          ← ADD THIS
├── templates/
└── requirements.txt
```

### 2. Set Environment Variables on Railway

Go to your Railway project → Variables tab, add:

```bash
AVIAPAGES_API_KEY=your_aviapages_token_here
VILLERS_JETS_AFFILIATE_URL=https://www.villersjets.com/?ref=YOUR_AFFILIATE_ID
```

**Important:** Replace `YOUR_AFFILIATE_ID` with your actual Villers Jets tracking ID

### 3. Apply Code Changes

Open `Luxury_Travel_Bot.py` and make these changes:

#### A. Add Import (after line 16)
```python
from flight_scraper import FlightScraper, format_flight_response
```

#### B. Add Flight Parameter Extraction (after `extract_parameters` function ~line 700)
```python
def extract_flight_parameters(message: str) -> dict:
    """Extract flight parameters."""
    import re
    params = {
        "origin": None,
        "destination": None,
        "departure_date": None,
        "passengers": 4,
        "aircraft_type": None,
        "search_empty_legs": "empty leg" in message.lower()
    }
    
    # Passenger count
    match = re.search(r'(\d+)\s*(?:passenger|pax|people|person)', message.lower())
    if match:
        params["passengers"] = int(match.group(1))
    
    # Route: "from X to Y" or "X to Y"
    match = re.search(r'from\s+([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+?)(?:\s|$|,)', message, re.IGNORECASE)
    if not match:
        match = re.search(r'([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+?)(?:\s|$|,)', message, re.IGNORECASE)
    
    if match:
        params["origin"] = match.group(1).strip()
        params["destination"] = match.group(2).strip()
    
    return params
```

#### C. Add Flight Generation (after `generate_getaway` function ~line 1000)
```python
def generate_flight_quote(flight_params: dict) -> str:
    """Generate flight quote."""
    scraper = FlightScraper()
    
    if flight_params.get("search_empty_legs"):
        empty_legs = scraper.search_empty_legs()
        if not empty_legs.get("empty_legs"):
            return (
                "✈️ **Empty Leg Deals**\n\n"
                "Contact Villers Jets for current availability:\n"
                f"{empty_legs.get('affiliate_link')}\n\n"
                "Save up to 75% on private jet travel!"
            )
        
        content = ["✈️ **Current Empty Leg Deals**\n"]
        for deal in empty_legs["empty_legs"][:5]:
            content.append(f"• {deal['route']} - ${deal['price']:,.0f}\n")
        content.append(f"\n🔗 {empty_legs['affiliate_link']}")
        return "\n".join(content)
    
    origin = flight_params.get("origin")
    destination = flight_params.get("destination")
    
    if not origin or not destination:
        return (
            "I'd be happy to find you a private jet! Please provide:\n"
            "• Departure city\n• Destination city\n\n"
            "Example: 'Private jet from Miami to Aspen for 6 passengers'"
        )
    
    results = scraper.search_flights(
        origin=origin,
        destination=destination,
        departure_date=flight_params.get("departure_date"),
        passengers=flight_params.get("passengers", 4),
        aircraft_type=flight_params.get("aircraft_type")
    )
    
    return scraper.format_for_chat(results)
```

#### D. Update Chat Route (replace existing `/api/chat` route ~line 1390)
```python
@app.route("/api/chat", methods=["POST"])
def chat():
    """Main chat endpoint."""
    try:
        data = request.get_json()
        message = data.get("message", "")
        
        if not message:
            return jsonify({"error": "Message required"}), 400
        
        logger.info(f"Chat: {message}")
        message_lower = message.lower()
        
        # CHECK FOR FLIGHTS FIRST
        flight_keywords = ["private jet", "charter", "flight", "fly", "aircraft", "empty leg"]
        if any(kw in message_lower for kw in flight_keywords):
            flight_params = extract_flight_parameters(message)
            content = generate_flight_quote(flight_params)
            return jsonify({
                "response": content,
                "parameters": flight_params,
                "intent": "flight"
            })
        
        # Rest of your existing code for itineraries/getaways...
        parameters = extract_parameters(message)
        
        if any(w in message_lower for w in ["getaway", "vacation", "escape", "weekend"]):
            content = generate_getaway(parameters)
            doc_type = "getaway"
        elif any(w in message_lower for w in ["itinerary", "plan", "trip", "schedule"]):
            content = generate_itinerary(parameters)
            doc_type = "itinerary"
        else:
            return jsonify({
                "response": (
                    "Hi! I'm Dave from Eco Friendly Luxury Travels. I can:\n\n"
                    "📅 Create sustainable travel itineraries\n"
                    "🏖️ Suggest eco-friendly luxury getaways\n"
                    "✈️ Find private jet charters\n\n"  # ← ADDED THIS LINE
                    "What would you like to explore?"
                ),
                "parameters": parameters
            })
        
        # Existing PDF generation code continues...
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500
```

### 4. Push to Railway

```bash
git add flight_scraper.py Luxury_Travel_Bot.py
git commit -m "Add private jet flight search with Villers Jets affiliate"
git push
```

Railway will auto-deploy. Check logs for any errors.

---

## 🧪 Testing

Test with these messages in your chatbot:

```
✈️ "Find me a private jet from Miami to Aspen"
✈️ "Show me empty leg deals"
✈️ "Charter flight from New York to Dubai for 8 passengers"
✈️ "Private jet to Bali leaving tomorrow"
```

---

## 📊 Tracking Conversions

Your Villers Jets affiliate link automatically includes tracking via:
- Your affiliate ID in the URL
- UTM parameters: `utm_source=ecofriendly&utm_medium=chatbot`
- Route info for better attribution

Check your Villers Jets dashboard for conversion tracking.

---

## 🎯 Next Steps (Optional Enhancements)

1. **Add Flight PDF Generation**
   - Create branded flight quotes in PDF format
   - Include Villers Jets branding

2. **Frontend Widget**
   - Add dedicated "Private Jets" search form on your website
   - Quick search: Origin → Destination → Date

3. **Email Notifications**
   - Alert users when empty legs match their routes
   - Build email list for remarketing

4. **Price Comparison**
   - Show "vs First Class" pricing comparison
   - Highlight time savings

---

## 🔧 Troubleshooting

**Issue:** API returns 401 error
**Fix:** Check `AVIAPAGES_API_KEY` is set correctly in Railway

**Issue:** No flight results
**Fix:** Fallback response shows Villers Jets link (this is expected for free tier)

**Issue:** Module import error
**Fix:** Ensure `flight_scraper.py` is in the same directory as `Luxury_Travel_Bot.py`

---

## 📞 Support

Questions? Check:
- Aviapages API Docs: https://docs.aviapages.com
- Villers Jets Affiliate: [Your affiliate dashboard]

---

**Integration Time:** ~5 minutes  
**Deployment:** Automatic via Railway  
**Status:** ✅ Ready for production