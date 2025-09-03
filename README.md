# Travel Agent API 🧳✈️

A **FastAPI-based travel planner** that generates a complete itinerary and packing list for any destination.
It combines **free data sources** (weather, POIs) with **optional APIs** (events, LLM polish) to make trip planning dynamic and robust.

---

## 🚀 Features

* **Geocoding & Weather** → [Open-Meteo](https://open-meteo.com/) (free, no key)
* **Points of Interest** → [Wikipedia / MediaWiki GeoSearch](https://www.mediawiki.org/wiki/API:Main_page) (free, no key)
* **Events** → [Ticketmaster Discovery API](https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/) (optional free key)
* **Itinerary polish** → [OpenAI](https://platform.openai.com/) (optional key, for better wording only)
* **Async & resilient** → Uses `httpx` + `tenacity` for concurrency, retries, and timeouts
* **Graceful fallback** → Runs fine with no keys at all; enriches results if keys are present

---

## 🛠 Tech Stack

* **FastAPI** – Web API framework
* **Pydantic v2** – Validation & settings management
* **httpx** – Async HTTP client
* **tenacity** – Retry & backoff
* **LangChain / LangGraph** (optional) – For LLM polish
* **ngrok** (optional) – For exposing local API globally

---

## 📂 Project Structure

```
Travel_Agent/
│
├── app.py            # FastAPI app & logic
├── main.py           #sample skeleton 
├── requirements.txt   # Dependencies
├── .env.example       # Example env file (copy to .env and fill keys)
├── Travel_Agent_Output.pdf  # Example run output
└── README.md          # Documentation
```

---

## ⚙️ Setup & Run

1. **Clone the repo**

   ```bash
   git clone https://github.com/your-username/Travel_Agent.git
   cd Travel_Agent
   ```

2. **Create virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Mac/Linux
   .venv\Scripts\Activate.ps1  # Windows PowerShell
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure `.env` (optional keys)**

   ```env
   OPENAI_API_KEY=sk-...              # Optional: improves text polish
   TICKETMASTER_API_KEY=your_key_here # Optional: enriches evenings with events
   ```

5. **Run FastAPI**

   ```bash
   uvicorn app:app --reload
   ```

6. **Open docs**

   * Local: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   * If using ngrok: `https://<your-ngrok-id>.ngrok-free.app/docs`

---

## 📤 Example Request

**POST** `/plan-trip`

```json
{
  "destination": "Tokyo",
  "days": 5
}
```

---

## 📥 Example Output (excerpt)

```json
 {
  "destination": "Tokyo",
  "days": 5,
  "itinerary": "Trip to Tokyo — 5 day(s) itinerary:\nDay 1: Morning—City walk; Afternoon—Top landmark; Evening—Local food crawl.\nDay 2: Morning—City walk; Afternoon—Top landmark; Evening—Local food crawl.\nDay 3: Morning—City walk; Afternoon—Top landmark; Evening—Local food crawl.\nDay 4: Morning—City walk; Afternoon—Top landmark; Evening—Local food crawl.\nDay 5: Morning—City walk; Afternoon—Top landmark; Evening—Local food crawl.",
  "packing_list": "Essentials: Passport/ID, wallet, phone, charger, meds.\nClothing: 3–5 outfits, comfy walking shoes, light jacket.\nToiletries: toothbrush, toothpaste, sunscreen, deodorant.\nDestination-specific for Tokyo: small umbrella, reusable water bottle."
}

 {
  "destination": "Tokyo, Japan",
  "days": 5,
  "summary": "Tokyo, Japan: First day looks partly cloudy, 33/25°C with 0mm precip.. 8 sights nearby, 0 events found.",
  "daily_itinerary": [
    {
      "day": 1,
      "date": "2025-09-03",
      "morning": "Explore: Tokyo",
      "afternoon": "Visit: Greater Tokyo Area",
      "evening": "Tokyo subway sarin attack",
      "meals": [
        "Local bakery breakfast",
        "Regional specialty lunch",
        "Well-reviewed dinner spot"
      ]
    },
    {
      "day": 2,
      "date": "2025-09-04",
      "morning": "Explore: Tokyo Metropolitan Government Building",
      "afternoon": "Visit: Tokyo Metropolitan Government",
      "evening": "Tochōmae Station",
      "meals": [
        "Local bakery breakfast",
        "Regional specialty lunch",
        "Well-reviewed dinner spot"
      ]
    },
    {
      "day": 3,
      "date": "2025-09-05",
      "morning": "Explore: 47th All Japan Rugby Football Championship",
      "afternoon": "Visit: Shinjuku Niagara Falls",
      "evening": "Tokyo",
      "meals": [
        "Local bakery breakfast",
        "Regional specialty lunch",
        "Well-reviewed dinner spot"
      ]
    },
    {
      "day": 4,
      "date": "2025-09-06",
      "morning": "Explore: Greater Tokyo Area",
      "afternoon": "Visit: Tokyo subway sarin attack",
      "evening": "Tokyo Metropolitan Government Building",
      "meals": [
        "Local bakery breakfast",
        "Regional specialty lunch",
        "Well-reviewed dinner spot"
      ]
    },
    {
      "day": 5,
      "date": "2025-09-07",
      "morning": "Explore: Tokyo Metropolitan Government",
      "afternoon": "Visit: Tochōmae Station",
      "evening": "47th All Japan Rugby Football Championship",
      "meals": [
        "Local bakery breakfast",
        "Regional specialty lunch",
        "Well-reviewed dinner spot"
      ]
    }
  ],
  "packing_list": {
    "essentials": [
      "Passport/ID",
      "Wallet",
      "Phone + charger",
      "Meds",
      "Reusable bottle",
      "Compact umbrella / rain jacket"
    ],
    "clothing": [
      "Walking shoes",
      "Socks/underwear",
      "Tops/bottoms",
      "Hat & sunglasses; light fabrics"
    ],
    "toiletries": [
      "Toothbrush/toothpaste",
      "Deodorant",
      "Sunscreen"
    ],
    "electronics": [
      "Power adapter",
      "Power bank"
    ]
  },
  "context": {
    "geo": {
      "name": "Tokyo",
      "country": "Japan",
      "lat": 35.6895,
      "lon": 139.69171,
      "timezone": "Asia/Tokyo"
    },
    "forecast": [
      {
        "date": "2025-09-03",
        "temp_day_c": 33,
        "temp_night_c": 24.6,
        "condition": "Partly cloudy",
        "precipitation_mm": 0
      },
      {
        "date": "2025-09-04",
        "temp_day_c": 27.9,
        "temp_night_c": 24.9,
        "condition": "Drizzle",
        "precipitation_mm": 0.4
      },
      {
        "date": "2025-09-05",
        "temp_day_c": 30.9,
        "temp_night_c": 24.5,
        "condition": "Rain",
        "precipitation_mm": 92.4
      },
      {
        "date": "2025-09-06",
        "temp_day_c": 31.6,
        "temp_night_c": 22.2,
        "condition": "Partly cloudy",
        "precipitation_mm": 0
      },
      {
        "date": "2025-09-07",
        "temp_day_c": 32.6,
        "temp_night_c": 24.8,
        "condition": "Partly cloudy",
        "precipitation_mm": 0
      }
    ],
    "pois": [
      {
        "name": "Tokyo",
        "summary": "Tokyo, officially the Tokyo Metropolis, is the capital and most populous city in Japan. With a population of over 14 million in the city proper in 2023, it is one of the most populous urban areas in the world. The Greater Tokyo Area, which includes Tokyo and parts of six neighboring prefectures, is the most populous metropolitan area in the world, with 41 million residents as of 2024.\nLying at the head of Tokyo Bay, Tokyo is part of the Kantō region, on the central coast of Honshu, Japan's largest island. It is Japan's economic center and the seat of the Japanese government and the Emperor of ",
        "distance_km": 0.05,
        "url": "https://en.wikipedia.org/wiki/Tokyo"
      },
      {
        "name": "Greater Tokyo Area",
        "summary": "The Greater Tokyo Area is the most populous metropolitan area in the world, consisting of the Kantō region of Japan (including Tokyo Metropolis and the prefectures of Chiba, Gunma, Ibaraki, Kanagawa, Saitama, and Tochigi) as well as the prefecture of Yamanashi of the neighboring Chūbu region. In Japanese, it is referred to by various terms, one of the most common being Capital Region (首都圏, Shuto-ken).\nAs of 2016, the United Nations estimates the total population at 38,140,000. It covers an area of approximately 13,500 km2 (5,200 mi2), giving it a population density of 2,642 people/km2. It is t",
        "distance_km": 0.03,
        "url": "https://en.wikipedia.org/wiki/Greater_Tokyo_Area"
      },
      {
        "name": "Tokyo subway sarin attack",
        "summary": "The Tokyo subway sarin attack (Japanese: 地下鉄サリン事件, Hepburn: Chikatetsu sarin jiken; lit. 'subway sarin incident') was a chemical domestic terrorist attack perpetrated on 20 March 1995, in Tokyo, Japan, by members of the Aum Shinrikyo cult. In five coordinated attacks, the perpetrators released sarin on three lines of the Tokyo Metro (then Teito Rapid Transit Authority) during rush hour, killing 13 people, severely injuring 50 (some of whom later died), and causing temporary vision problems for nearly 1,000 others. The attack was directed against trains passing through Kasumigaseki and Nagatach",
        "distance_km": 0.01,
        "url": "https://en.wikipedia.org/wiki/Tokyo_subway_sarin_attack"
      },
      {
        "name": "Tokyo Metropolitan Government Building",
        "summary": "The Tokyo Metropolitan Government Building (東京都庁舎, Tōkyō-to Chōsha), also referred to as the Tochō (都庁) for short, is the seat of the Tokyo Metropolitan Government, which governs the special wards, cities, towns, and villages that constitute the Tokyo Metropolis.\nLocated in Shinjuku ward, the building was designed by architect Kenzo Tange. It consists of a complex of three structures, each taking up a city block. The tallest of the three is the Tokyo Metropolitan Government Building No.1, a tower 48 stories tall that splits into two sections at the 33rd floor. The building also has three level",
        "distance_km": 0.05,
        "url": "https://en.wikipedia.org/wiki/Tokyo_Metropolitan_Government_Building"
      },
      {
        "name": "Tokyo Metropolitan Government",
        "summary": "The Tokyo Metropolitan Government (東京都庁, Tōkyōto-chō) is the government of the Tokyo Metropolis. One of the 47 prefectures of Japan, the government consists of a popularly elected governor and assembly. The headquarters building is located in the ward of Shinjuku. The metropolitan government administers the special wards, cities, towns and villages that constitute part of the Tokyo Metropolis.  With a population closing in on 14 million living within its boundaries, and many more commuting from neighbouring prefectures, the metropolitan government wields significant political power within Japa",
        "distance_km": 0.01,
        "url": "https://en.wikipedia.org/wiki/Tokyo_Metropolitan_Government"
      },
      {
        "name": "Tochōmae Station",
        "summary": "Tochōmae Station (都庁前駅, Tochōmae-eki; Metropolitan Government Station) is a subway station on the Toei Ōedo Line in Shinjuku, Tokyo, Japan, operated by the Tokyo subway operator Toei Subway. The name of this station suggests its location in front of the Tokyo Metropolitan Government Building, and it is the nearest station to that complex.\nUnusually, the station is both a terminus and a through station on the same line. Inbound trains pass through the station, travel south to complete a counterclockwise loop around central Tokyo, and terminate at Tochōmae. Outbound trains do the opposite, depar",
        "distance_km": 0.16,
        "url": "https://en.wikipedia.org/wiki/Toch%C5%8Dmae_Station"
      },
      {
        "name": "47th All Japan Rugby Football Championship",
        "summary": "The 2010 The All-Japan Rugby Football Championship (日本ラグビーフットボール選手権大会 Nihon Ragubi- Futtobo-ru Senshuken Taikai) starts on Feb 6th and finishes with the final on Feb 27th.",
        "distance_km": 0,
        "url": "https://en.wikipedia.org/wiki/47th_All_Japan_Rugby_Football_Championship"
      },
      {
        "name": "Shinjuku Niagara Falls",
        "summary": "Shinjuku Niagara Falls is a fountain in Tokyo's Shinjuku Central Park, in Shinjuku, Japan. The Tokyo Weekender has described the water feature as \"generously named\".",
        "distance_km": 0.2,
        "url": "https://en.wikipedia.org/wiki/Shinjuku_Niagara_Falls"
      }
    ],
    "events": [],
    "providers": {
      "geocoding": "Open-Meteo (free)",
      "forecast": "Open-Meteo (free)",
      "pois": "Wikipedia GeoSearch (free)",
      "events": "Ticketmaster Discovery (optional)",
      "polish": "OpenAI (optional)"
    }
  }
}


```

*(See `Travel_Agent_Output.pdf` for full example output.)*

---

## 🔒 Security Notes

* Add `.env` to `.gitignore` so your secrets never get pushed.
* Use `.env.example` to show required variables without exposing keys.
* If exposing via ngrok, consider adding an API key check on your endpoint.

---

## 🌍 Next Improvements

* Add [OpenTripMap](https://opentripmap.io/) API for richer POIs (free tier).
* Integrate holiday calendars ([Nager.Date](https://date.nager.at/)).
* Add currency info ([ExchangeRate.host](https://exchangerate.host/)).
* Cache API results to reduce requests.

---

✨ Built with ❤️ using free + optional trial APIs to make trip planning smarter and more robust.

---

Would you also like me to give you a **ready-made `.gitignore` file** content to paste, so you don’t accidentally commit `.env` or `.venv`?
