"""
Script to generate 300 real cricket players with images.
Run this ONCE after init_db() to populate the players table.

Usage:
    python seed_players.py
"""

import sqlite3
import random
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

# ---------------- REAL PLAYER POOL ----------------
# Real cricketer names with role assigned.
# Images use Wikipedia/ESPNcricinfo style placeholder avatars via randomuser/ui-avatars
# (Using ui-avatars.com to generate consistent avatar images with player initials - works without API key)

REAL_PLAYERS = [
    ("Virat Kohli", "Batsman"), ("Rohit Sharma", "Batsman"), ("MS Dhoni", "Wicketkeeper"),
    ("Jasprit Bumrah", "Bowler"), ("Hardik Pandya", "All-rounder"), ("KL Rahul", "Wicketkeeper"),
    ("Ravindra Jadeja", "All-rounder"), ("Shubman Gill", "Batsman"), ("Rishabh Pant", "Wicketkeeper"),
    ("Mohammed Shami", "Bowler"), ("Suryakumar Yadav", "Batsman"), ("Yuzvendra Chahal", "Bowler"),
    ("Bhuvneshwar Kumar", "Bowler"), ("Shreyas Iyer", "Batsman"), ("Axar Patel", "All-rounder"),
    ("David Warner", "Batsman"), ("Steve Smith", "Batsman"), ("Pat Cummins", "Bowler"),
    ("Mitchell Starc", "Bowler"), ("Glenn Maxwell", "All-rounder"), ("Marcus Stoinis", "All-rounder"),
    ("David Miller", "Batsman"), ("Quinton de Kock", "Wicketkeeper"), ("Kagiso Rabada", "Bowler"),
    ("Faf du Plessis", "Batsman"), ("Aiden Markram", "Batsman"), ("Anrich Nortje", "Bowler"),
    ("Joe Root", "Batsman"), ("Ben Stokes", "All-rounder"), ("Jos Buttler", "Wicketkeeper"),
    ("Jofra Archer", "Bowler"), ("Jonny Bairstow", "Wicketkeeper"), ("Moeen Ali", "All-rounder"),
    ("Sam Curran", "All-rounder"), ("Liam Livingstone", "All-rounder"), ("Kane Williamson", "Batsman"),
    ("Trent Boult", "Bowler"), ("Devon Conway", "Batsman"), ("Tim Southee", "Bowler"),
    ("Daryl Mitchell", "All-rounder"), ("Mitchell Santner", "All-rounder"), ("Babar Azam", "Batsman"),
    ("Shaheen Afridi", "Bowler"), ("Mohammad Rizwan", "Wicketkeeper"), ("Shadab Khan", "All-rounder"),
    ("Fakhar Zaman", "Batsman"), ("Rashid Khan", "Bowler"), ("Mujeeb Ur Rahman", "Bowler"),
    ("Mohammad Nabi", "All-rounder"), ("Wanindu Hasaranga", "All-rounder"), ("Dasun Shanaka", "All-rounder"),
    ("Pathum Nissanka", "Batsman"), ("Shakib Al Hasan", "All-rounder"), ("Litton Das", "Wicketkeeper"),
    ("Mustafizur Rahman", "Bowler"), ("Nicholas Pooran", "Wicketkeeper"), ("Sunil Narine", "All-rounder"),
    ("Andre Russell", "All-rounder"), ("Jason Holder", "All-rounder"), ("Shimron Hetmyer", "Batsman"),
    ("Kieron Pollard", "All-rounder"), ("Dwayne Bravo", "All-rounder"), ("Chris Gayle", "Batsman"),
    ("AB de Villiers", "Batsman"), ("Yuvraj Singh", "All-rounder"), ("Gautam Gambhir", "Batsman"),
    ("Sachin Tendulkar", "Batsman"), ("Rahul Dravid", "Batsman"), ("Sourav Ganguly", "Batsman"),
    ("Anil Kumble", "Bowler"), ("Zaheer Khan", "Bowler"), ("Harbhajan Singh", "Bowler"),
    ("Virender Sehwag", "Batsman"), ("Irfan Pathan", "All-rounder"), ("Suresh Raina", "All-rounder"),
    ("Ajinkya Rahane", "Batsman"), ("Cheteshwar Pujara", "Batsman"), ("Umesh Yadav", "Bowler"),
    ("Ishant Sharma", "Bowler"), ("Kuldeep Yadav", "Bowler"), ("Washington Sundar", "All-rounder"),
    ("Deepak Chahar", "Bowler"), ("Prithvi Shaw", "Batsman"), ("Devdutt Padikkal", "Batsman"),
    ("Ruturaj Gaikwad", "Batsman"), ("Yashasvi Jaiswal", "Batsman"), ("Tilak Varma", "Batsman"),
    ("Arshdeep Singh", "Bowler"), ("Mohammed Siraj", "Bowler"), ("Avesh Khan", "Bowler"),
    ("Shardul Thakur", "All-rounder"), ("T Natarajan", "Bowler"), ("Sanju Samson", "Wicketkeeper"),
    ("Ishan Kishan", "Wicketkeeper"), ("Venkatesh Iyer", "All-rounder"), ("Rinku Singh", "Batsman"),
    ("Mitchell Marsh", "All-rounder"), ("Travis Head", "Batsman"), ("Marnus Labuschagne", "Batsman"),
    ("Adam Zampa", "Bowler"), ("Josh Hazlewood", "Bowler"), ("Cameron Green", "All-rounder"),
    ("Matthew Wade", "Wicketkeeper"), ("Alex Carey", "Wicketkeeper"), ("Tim David", "Batsman"),
    ("Eoin Morgan", "Batsman"), ("Chris Woakes", "All-rounder"), ("Mark Wood", "Bowler"),
    ("Adil Rashid", "Bowler"), ("Harry Brook", "Batsman"), ("Phil Salt", "Wicketkeeper"),
    ("Reece Topley", "Bowler"), ("Lockie Ferguson", "Bowler"), ("Ish Sodhi", "Bowler"),
    ("Glenn Phillips", "Wicketkeeper"), ("James Neesham", "All-rounder"), ("Finn Allen", "Batsman"),
    ("Imam-ul-Haq", "Batsman"), ("Haris Rauf", "Bowler"), ("Naseem Shah", "Bowler"),
    ("Iftikhar Ahmed", "All-rounder"), ("Imad Wasim", "All-rounder"), ("Charith Asalanka", "Batsman"),
    ("Maheesh Theekshana", "Bowler"), ("Dushmantha Chameera", "Bowler"), ("Kusal Mendis", "Wicketkeeper"),
    ("Bhanuka Rajapaksa", "Batsman"), ("Najmul Hossain Shanto", "Batsman"), ("Taskin Ahmed", "Bowler"),
    ("Towhid Hridoy", "Batsman"), ("Mehidy Hasan", "All-rounder"), ("Brandon King", "Batsman"),
    ("Shai Hope", "Wicketkeeper"), ("Alzarri Joseph", "Bowler"), ("Romario Shepherd", "All-rounder"),
    ("Akeal Hosein", "Bowler"), ("Obed McCoy", "Bowler"), ("Rovman Powell", "All-rounder"),
    ("Heinrich Klaasen", "Wicketkeeper"), ("Tabraiz Shamsi", "Bowler"), ("Lungi Ngidi", "Bowler"),
    ("Reeza Hendricks", "Batsman"), ("Tristan Stubbs", "Batsman"), ("Marco Jansen", "All-rounder"),
    ("Gerald Coetzee", "Bowler"), ("Wiaan Mulder", "All-rounder"), ("Keshav Maharaj", "Bowler"),
    ("Mark Boucher", "Wicketkeeper"), ("Jacques Kallis", "All-rounder"), ("Graeme Smith", "Batsman"),
    ("Shane Watson", "All-rounder"), ("Brett Lee", "Bowler"), ("Ricky Ponting", "Batsman"),
    ("Michael Clarke", "Batsman"), ("Adam Gilchrist", "Wicketkeeper"), ("Brad Haddin", "Wicketkeeper"),
    ("Shaun Marsh", "Batsman"), ("Aaron Finch", "Batsman"), ("James Pattinson", "Bowler"),
    ("Nathan Lyon", "Bowler"), ("Marcus Harris", "Batsman"), ("Usman Khawaja", "Batsman"),
    ("Will Pucovski", "Batsman"), ("Cameron Bancroft", "Batsman"), ("Josh Inglis", "Wicketkeeper"),
    ("Matthew Renshaw", "Batsman"), ("Spencer Johnson", "Bowler"), ("Jhye Richardson", "Bowler"),
    ("Sean Abbott", "Bowler"), ("Daniel Sams", "All-rounder"), ("Ben Dwarshuis", "Bowler"),
    ("Riley Meredith", "Bowler"), ("Ashton Agar", "All-rounder"), ("Matthew Kuhnemann", "Bowler"),
    ("Todd Murphy", "Bowler"), ("Cooper Connolly", "All-rounder"), ("Jake Fraser-McGurk", "Batsman"),
    ("Tanveer Sangha", "Bowler"), ("Aaron Hardie", "All-rounder"), ("Lance Morris", "Bowler"),
    ("Nathan Ellis", "Bowler"), ("Will Sutherland", "All-rounder"), ("Ben McDermott", "Wicketkeeper"),
    ("Matthew Short", "All-rounder"), ("Jake Weatherald", "Batsman"), ("Henry Hunt", "Batsman"),
    ("Jack Edwards", "All-rounder"), ("Param Uppal", "Batsman"), ("Cameron Bancroft Jr", "Batsman"),
    ("Sam Konstas", "Batsman"), ("Hilton Cartwright", "All-rounder"), ("Liam Hatcher", "Bowler"),
    ("Ben Sears", "Bowler"), ("Will Young", "Batsman"), ("Tom Latham", "Wicketkeeper"),
    ("Henry Nicholls", "Batsman"), ("Rachin Ravindra", "All-rounder"), ("Matt Henry", "Bowler"),
    ("Adam Milne", "Bowler"), ("Ben Lister", "Bowler"), ("Kyle Jamieson", "Bowler"),
    ("Michael Bracewell", "All-rounder"), ("Tom Bruce", "All-rounder"), ("Mark Chapman", "Batsman"),
    ("George Munsey", "Batsman"), ("Richie Berrington", "All-rounder"), ("Brad Wheal", "Bowler"),
    ("Chris Sole", "Bowler"), ("Mark Watt", "Bowler"), ("Calum MacLeod", "Batsman"),
    ("Mohammad Hafeez", "All-rounder"), ("Shoaib Malik", "All-rounder"), ("Sarfaraz Ahmed", "Wicketkeeper"),
    ("Hasan Ali", "Bowler"), ("Wahab Riaz", "Bowler"), ("Mohammad Amir", "Bowler"),
    ("Asif Ali", "Batsman"), ("Khushdil Shah", "All-rounder"), ("Saud Shakeel", "Batsman"),
    ("Abdullah Shafique", "Batsman"), ("Mohammad Wasim Jr", "Bowler"), ("Zaman Khan", "Bowler"),
    ("Abrar Ahmed", "Bowler"), ("Usama Mir", "Bowler"), ("Salman Agha", "All-rounder"),
    ("Mohammad Haris", "Wicketkeeper"), ("Azam Khan", "Wicketkeeper"), ("Tayyab Tahir", "Batsman"),
    ("Faheem Ashraf", "All-rounder"), ("Saim Ayub", "Batsman"), ("Sahibzada Farhan", "Batsman"),
    ("Akif Javed", "Bowler"), ("Mohammad Ali", "Bowler"), ("Aamer Jamal", "All-rounder"),
    ("Imran Tahir", "Bowler"), ("Albie Morkel", "All-rounder"), ("Morne Morkel", "Bowler"),
    ("Dale Steyn", "Bowler"), ("Hashim Amla", "Batsman"), ("JP Duminy", "All-rounder"),
    ("Colin Ingram", "Batsman"), ("Robin Peterson", "Bowler"), ("Vernon Philander", "Bowler"),
    ("Wayne Parnell", "Bowler"), ("Lonwabo Tsotsobe", "Bowler"), ("Farhaan Behardien", "All-rounder"),
    ("Rilee Rossouw", "Batsman"), ("Andile Phehlukwayo", "All-rounder"), ("Lutho Sipamla", "Bowler"),
    ("Sisanda Magala", "Bowler"), ("Donovan Ferreira", "Wicketkeeper"), ("Dewald Brevis", "Batsman"),
    ("Ryan Rickelton", "Wicketkeeper"), ("Matthew Breetzke", "Batsman"), ("Corbin Bosch", "All-rounder"),
    ("Nandre Burger", "Bowler"), ("Ottneil Baartman", "Bowler"), ("George Linde", "All-rounder"),
    ("Bjorn Fortuin", "Bowler"), ("Senuran Muthusamy", "All-rounder"), ("Kyle Verreynne", "Wicketkeeper"),
    ("Khaya Zondo", "Batsman"), ("Theunis de Bruyn", "Batsman"), ("Zubayr Hamza", "Batsman"),
    ("Pite van Biljon", "Wicketkeeper"), ("Janneman Malan", "Batsman"), ("Jon-Jon Smuts", "All-rounder"),
    ("Eathan Bosch", "Bowler"), ("Beuran Hendricks", "Bowler"), ("David Wiese", "All-rounder"),
    ("Kyle Abbott", "Bowler"), ("Imran Khan Sr", "Bowler"), ("Wasim Akram", "Bowler"),
    ("Waqar Younis", "Bowler"), ("Inzamam-ul-Haq", "Batsman"), ("Saeed Anwar", "Batsman"),
    ("Younis Khan", "Batsman"), ("Misbah-ul-Haq", "Batsman"), ("Shahid Afridi", "All-rounder"),
    ("Brian Lara", "Batsman"), ("Curtly Ambrose", "Bowler"), ("Courtney Walsh", "Bowler"),
    ("Viv Richards", "Batsman"), ("Carl Hooper", "All-rounder"), ("Ramnaresh Sarwan", "Batsman"),
    ("Chris Jordan", "Bowler"), ("Tymal Mills", "Bowler"), ("David Willey", "All-rounder"),
    ("Saqib Mahmood", "Bowler"), ("Olly Stone", "Bowler"), ("Will Jacks", "All-rounder"),
    ("Rehan Ahmed", "Bowler"), ("Jacob Bethell", "All-rounder"), ("Jamie Smith", "Wicketkeeper"),
    ("Dan Lawrence", "Batsman"), ("Jordan Cox", "Wicketkeeper"), ("Tom Banton", "Wicketkeeper"),
    ("Alex Hales", "Batsman"), ("Jason Roy", "Batsman"), ("James Vince", "Batsman"),
    ("Brydon Carse", "Bowler"), ("Gus Atkinson", "Bowler"), ("Josh Tongue", "Bowler"),
    ("Sonny Baker", "Bowler"), ("Luke Wood", "Bowler"), ("John Turner", "Bowler"),
    ("Liam Dawson", "All-rounder"), ("Lewis Gregory", "All-rounder"), ("Craig Overton", "All-rounder"),
    ("Tom Curran", "All-rounder"), ("Ollie Pope", "Batsman"), ("Zak Crawley", "Batsman"),
    ("Ben Duckett", "Batsman"), ("Dawid Malan", "Batsman")
]

ROLES_VALID = ["Batsman", "Bowler", "All-rounder", "Wicketkeeper"]


def random_skill(role, base):
    """Generate skill values based on role and base rating."""
    variance = random.randint(-10, 10)
    val = max(20, min(99, base + variance))
    return val


def generate_players():
    """Insert 300 real players into the database with stats and images."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Clear existing players (fresh seed)
    cur.execute("DELETE FROM players")
    cur.execute("UPDATE teams SET budget = 120, matches_played=0, wins=0, losses=0, points=0, nrr=0.0")

    players_list = REAL_PLAYERS.copy()

    # If less than 300, repeat with suffixes to reach exactly 300
    idx = 1
    while len(players_list) < 300:
        base_name, base_role = REAL_PLAYERS[idx % len(REAL_PLAYERS)]
        players_list.append((f"{base_name} Jr {idx}", base_role))
        idx += 1

    players_list = players_list[:300]

    for name, role in players_list:
        if role not in ROLES_VALID:
            role = "All-rounder"

        # Overall rating between 50-99
        rating = random.randint(50, 99)

        # Skill values based on role
        if role == "Batsman":
            batting = random_skill(role, rating)
            bowling = random.randint(20, 50)
            fielding = random_skill(role, rating - 5)
        elif role == "Bowler":
            bowling = random_skill(role, rating)
            batting = random.randint(20, 50)
            fielding = random_skill(role, rating - 5)
        elif role == "Wicketkeeper":
            batting = random_skill(role, rating)
            bowling = random.randint(15, 35)
            fielding = random_skill(role, rating + 2)
        else:  # All-rounder
            batting = random_skill(role, rating - 5)
            bowling = random_skill(role, rating - 5)
            fielding = random_skill(role, rating - 8)

        batting = min(99, max(20, batting))
        bowling = min(99, max(15, bowling))
        fielding = min(99, max(20, fielding))

        base_price = 2.0  # 2 Crore base price for all

        # Generate avatar image using ui-avatars (name initials, no API key required)
        initials = "".join([w[0] for w in name.split()[:2]])
        image_url = f"https://ui-avatars.com/api/?name={initials}&background=random&size=256&bold=true"

        cur.execute("""
            INSERT INTO players (name, role, rating, batting, bowling, fielding, base_price, image, team_id, is_sold, sold_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 0, 0)
        """, (name, role, rating, batting, bowling, fielding, base_price, image_url))

    conn.commit()
    conn.close()
    print(f"✅ Successfully inserted {len(players_list)} players into database.")


if __name__ == "__main__":
    generate_players()