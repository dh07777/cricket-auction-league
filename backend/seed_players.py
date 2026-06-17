import sqlite3
import random
import os

DB_PATH = os.environ.get("DB_PATH", "auction.db")

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
    ("Jacques Kallis", "All-rounder"), ("Graeme Smith", "Batsman"),
    ("Shane Watson", "All-rounder"), ("Brett Lee", "Bowler"), ("Ricky Ponting", "Batsman"),
    ("Michael Clarke", "Batsman"), ("Adam Gilchrist", "Wicketkeeper"), ("Brad Haddin", "Wicketkeeper"),
    ("Aaron Finch", "Batsman"), ("Nathan Lyon", "Bowler"), ("Usman Khawaja", "Batsman"),
    ("Spencer Johnson", "Bowler"), ("Jhye Richardson", "Bowler"), ("Sean Abbott", "Bowler"),
    ("Daniel Sams", "All-rounder"), ("Riley Meredith", "Bowler"), ("Ashton Agar", "All-rounder"),
    ("Jake Fraser-McGurk", "Batsman"), ("Aaron Hardie", "All-rounder"), ("Lance Morris", "Bowler"),
    ("Nathan Ellis", "Bowler"), ("Will Sutherland", "All-rounder"), ("Ben McDermott", "Wicketkeeper"),
    ("Matthew Short", "All-rounder"), ("Sam Konstas", "Batsman"), ("Hilton Cartwright", "All-rounder"),
    ("Ben Sears", "Bowler"), ("Will Young", "Batsman"), ("Tom Latham", "Wicketkeeper"),
    ("Henry Nicholls", "Batsman"), ("Rachin Ravindra", "All-rounder"), ("Matt Henry", "Bowler"),
    ("Adam Milne", "Bowler"), ("Kyle Jamieson", "Bowler"), ("Michael Bracewell", "All-rounder"),
    ("Mark Chapman", "Batsman"), ("Mohammad Hafeez", "All-rounder"), ("Shoaib Malik", "All-rounder"),
    ("Sarfaraz Ahmed", "Wicketkeeper"), ("Hasan Ali", "Bowler"), ("Wahab Riaz", "Bowler"),
    ("Mohammad Amir", "Bowler"), ("Khushdil Shah", "All-rounder"), ("Saud Shakeel", "Batsman"),
    ("Abdullah Shafique", "Batsman"), ("Zaman Khan", "Bowler"), ("Abrar Ahmed", "Bowler"),
    ("Usama Mir", "Bowler"), ("Salman Agha", "All-rounder"), ("Mohammad Haris", "Wicketkeeper"),
    ("Saim Ayub", "Batsman"), ("Faheem Ashraf", "All-rounder"), ("Aamer Jamal", "All-rounder"),
    ("Imran Tahir", "Bowler"), ("Dale Steyn", "Bowler"), ("Hashim Amla", "Batsman"),
    ("JP Duminy", "All-rounder"), ("Colin Ingram", "Batsman"), ("Wayne Parnell", "Bowler"),
    ("Rilee Rossouw", "Batsman"), ("Andile Phehlukwayo", "All-rounder"), ("Lutho Sipamla", "Bowler"),
    ("Dewald Brevis", "Batsman"), ("Ryan Rickelton", "Wicketkeeper"), ("Corbin Bosch", "All-rounder"),
    ("Nandre Burger", "Bowler"), ("George Linde", "All-rounder"), ("Kyle Verreynne", "Wicketkeeper"),
    ("Khaya Zondo", "Batsman"), ("Theunis de Bruyn", "Batsman"), ("Janneman Malan", "Batsman"),
    ("Wasim Akram", "Bowler"), ("Waqar Younis", "Bowler"), ("Inzamam-ul-Haq", "Batsman"),
    ("Saeed Anwar", "Batsman"), ("Younis Khan", "Batsman"), ("Misbah-ul-Haq", "Batsman"),
    ("Shahid Afridi", "All-rounder"), ("Brian Lara", "Batsman"), ("Curtly Ambrose", "Bowler"),
    ("Courtney Walsh", "Bowler"), ("Viv Richards", "Batsman"), ("Carl Hooper", "All-rounder"),
    ("Chris Jordan", "Bowler"), ("Tymal Mills", "Bowler"), ("David Willey", "All-rounder"),
    ("Saqib Mahmood", "Bowler"), ("Will Jacks", "All-rounder"), ("Rehan Ahmed", "Bowler"),
    ("Jacob Bethell", "All-rounder"), ("Jamie Smith", "Wicketkeeper"), ("Dan Lawrence", "Batsman"),
    ("Jordan Cox", "Wicketkeeper"), ("Alex Hales", "Batsman"), ("Jason Roy", "Batsman"),
    ("Brydon Carse", "Bowler"), ("Gus Atkinson", "Bowler"), ("Josh Tongue", "Bowler"),
    ("Liam Dawson", "All-rounder"), ("Lewis Gregory", "All-rounder"), ("Craig Overton", "All-rounder"),
    ("Tom Curran", "All-rounder"), ("Ollie Pope", "Batsman"), ("Zak Crawley", "Batsman"),
    ("Ben Duckett", "Batsman"), ("Dawid Malan", "Batsman"), ("James Vince", "Batsman"),
    ("Tom Banton", "Wicketkeeper"), ("Luke Wood", "Bowler"), ("Olly Stone", "Bowler"),
    ("Jos Hazlewood Jr", "Bowler"), ("Pat Rowe", "Batsman"), ("Sam Northeast", "Batsman"),
    ("Chris Benjamin", "Wicketkeeper"), ("Michael Pepper", "Wicketkeeper"), ("Ed Barnard", "All-rounder"),
    ("Ryan Higgins", "All-rounder"), ("Tom Abell", "Batsman"), ("George Garton", "Bowler"),
    ("Danny Briggs", "Bowler"), ("James Fuller", "Bowler"), ("Leus du Plooy", "Batsman"),
    ("Wayne Madsen", "Batsman"), ("Billy Godleman", "Batsman"), ("Matt Critchley", "All-rounder"),
    ("Anuj Dal", "All-rounder"), ("Alex Hughes", "All-rounder"), ("Ravi Bopara", "All-rounder"),
    ("Sir Alastair Cook", "Batsman"), ("Kevin Pietersen", "Batsman"), ("Andrew Flintoff", "All-rounder"),
    ("Graeme Swann", "Bowler"), ("Matthew Prior", "Wicketkeeper"), ("Paul Collingwood", "All-rounder"),
    ("Steve Harmison", "Bowler"), ("Simon Jones", "Bowler"), ("Ashley Giles", "Bowler"),
    ("Marcus Trescothick", "Batsman"), ("Nasser Hussain", "Batsman"), ("Mike Atherton", "Batsman"),
]

ROLES_VALID = ["Batsman", "Bowler", "All-rounder", "Wicketkeeper"]


def random_skill(base):
    val = base + random.randint(-10, 10)
    return max(20, min(99, val))


def generate_players():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("DELETE FROM players")
    cur.execute("UPDATE teams SET budget=120, matches_played=0, wins=0, losses=0, points=0, nrr=0.0")

    players_list = REAL_PLAYERS.copy()
    idx = 1
    while len(players_list) < 300:
        base_name, base_role = REAL_PLAYERS[idx % len(REAL_PLAYERS)]
        players_list.append((f"{base_name} Jr {idx}", base_role))
        idx += 1
    players_list = players_list[:300]

    for name, role in players_list:
        if role not in ROLES_VALID:
            role = "All-rounder"

        rating = random.randint(50, 99)

        if role == "Batsman":
            batting = random_skill(rating)
            bowling = random.randint(20, 50)
            fielding = random_skill(rating - 5)
        elif role == "Bowler":
            bowling = random_skill(rating)
            batting = random.randint(20, 50)
            fielding = random_skill(rating - 5)
        elif role == "Wicketkeeper":
            batting = random_skill(rating)
            bowling = random.randint(15, 35)
            fielding = random_skill(rating + 2)
        else:
            batting = random_skill(rating - 5)
            bowling = random_skill(rating - 5)
            fielding = random_skill(rating - 8)

        batting = min(99, max(20, batting))
        bowling = min(99, max(15, bowling))
        fielding = min(99, max(20, fielding))

        initials = "".join([w[0] for w in name.split()[:2]])
        image_url = f"https://ui-avatars.com/api/?name={initials}&background=random&size=256&bold=true"

        cur.execute("""
            INSERT INTO players (name, role, rating, batting, bowling, fielding, base_price, image, team_id, is_sold, sold_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 0, 0)
        """, (name, role, rating, batting, bowling, fielding, 2.0, image_url))

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ Successfully inserted {len(players_list)} players into SQLite database.")


if __name__ == "__main__":
    generate_players()