# 🏏 Cricbuzz LiveStats Dashboard

## Real-Time Cricket Analytics Platform

Cricbuzz LiveStats is a **Streamlit-based cricket analytics dashboard** that integrates the **Cricbuzz API (RapidAPI)** with a **MySQL database** to deliver live match information, player statistics, SQL analytics, and database management operations.

The application provides an interactive environment for exploring **live cricket data, player rankings, and advanced cricket analytics queries**.

---

# 📌 Project Overview

The dashboard allows users to:

- View **live and recent cricket matches**
- Analyze **top player rankings and statistics**
- Execute **25 SQL analytics queries**
- Perform **CRUD operations on player data**

The platform demonstrates integration between:

- **APIs**
- **SQL databases**
- **interactive dashboards**

---

# ⚙️ Technology Stack

## Programming Language

Python

## Libraries & Frameworks

- Streamlit
- Pandas
- Requests
- Python-dotenv
- MySQL Connector

## Tools

- RapidAPI (Cricbuzz API)
- MySQL Database
- Streamlit Dashboard
- SQL Analytics

---

# 🧩 Application Architecture

```
User Interface (Streamlit)
        ↓
API Integration (Cricbuzz RapidAPI)
        ↓
Data Processing (Python + Pandas)
        ↓
Database Layer (MySQL)
        ↓
Analytics & Visualization
```

---

# 📂 Project Structure

```
Cricbuzz-LiveStats
│
├── Home.py
│
├── pages/
│   ├── live_match.py
│   ├── Player_Stats.py
│   ├── sql_analytics.py
│   └── crud.py
│
├── utils/
│   └── db_connection.py
│
├── .env
└── README.md
```

---

# 🏠 Home Page

## Overview

The Home page serves as the **main navigation hub** for the application.

It displays:

- Dashboard introduction
- Quick navigation links
- Last opened timestamp

### Navigation Options

- 🟢 Live Match Page  
- ⭐ Top Player Stats  
- 📊 SQL Queries & Analytics  
- 🛠 CRUD Operations  

The page links allow users to quickly switch between the modules of the dashboard. :contentReference[oaicite:1]{index=1}

---

# 🟢 Live Match Page

## Features

The Live Match module fetches **live and recent cricket match data** from the Cricbuzz API.

Users can:

- View **live match details**
- See **venue and match status**
- View **current innings snapshot**
- Display **scorecards**

### Information Displayed

- Match format (Test / ODI / T20)
- Teams playing
- Venue and stadium
- Batting and bowling team
- Run rate
- Wickets
- Extras
- Current score

The page also includes **scorecard loading functionality** to display batting and bowling statistics. :contentReference[oaicite:2]{index=2}

---

# ⭐ Top Player Stats Page

## Rankings Module

Displays top international cricket rankings using the Cricbuzz API.

Users can filter rankings by:

- Format (Test / ODI / T20I)
- Role (Batsmen / Bowlers)

The rankings table displays:

- Rank
- Player name
- Country
- Rating points

---

## Player Stat Loader

Users can search for any cricket player.

The system retrieves:

- Player profile
- Career statistics
- Batting and bowling information
- Performance tables

The data is fetched dynamically from the Cricbuzz API. :contentReference[oaicite:3]{index=3}

---

# 📊 SQL Analytics Page

This module allows users to run **25 pre-built SQL analytics queries** on the cricket database.

The queries are categorized into three levels.

## Beginner Queries

Examples include:

- Players from India
- Recent matches
- Top ODI run scorers
- Venue capacity analysis

---

## Intermediate Queries

Examples include:

- All-rounders with high runs and wickets
- Player performance across formats
- Team home vs away wins
- Player yearly averages

---

## Advanced Queries

Examples include:

- Bowling economy analysis
- Player consistency analysis
- Recent performance trends
- Quarterly batting improvement

The results are displayed in **interactive tables using Streamlit**. :contentReference[oaicite:4]{index=4}

---

# 🛠 CRUD Operations Page

The CRUD module allows users to **manage player records** in the database.

Supported operations include:

### Create

Add a new player with:

- Name
- Role
- Batting style
- Bowling style
- Team ID

### Read

Search and display player records by name.

### Update

Edit existing player information.

### Delete

Remove a player record from the database.

The module uses SQL queries executed through a database connection utility. :contentReference[oaicite:5]{index=5}

---

# 🔌 API Integration

The dashboard connects to the **Cricbuzz API through RapidAPI**.

Required environment variables:

```
RAPIDAPI_KEY=your_api_key
RAPIDAPI_HOST=cricbuzz-cricket.p.rapidapi.com
```

These values should be stored in a `.env` file.

---

# ▶ Running the Application

## Step 1 — Install Dependencies

```
pip install -r requirements.txt
```

---

## Step 2 — Configure Environment Variables

Create a `.env` file.

```
RAPIDAPI_KEY=your_key
RAPIDAPI_HOST=cricbuzz-cricket.p.rapidapi.com
```

---

## Step 3 — Run Streamlit

```
streamlit run Home.py
```

---

# 📈 Key Features

- Real-time cricket match data
- Interactive analytics dashboard
- Player ranking and statistics
- SQL-based cricket data analysis
- Database CRUD management
- API + Database integration

---

# 👨‍💻 Author

Ajey Jha

Data Science | Analytics | Machine Learning
