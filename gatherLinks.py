import sqlite3
import time
from urllib.request import urlopen
from bs4 import BeautifulSoup

conn = sqlite3.connect("SteamDB.sqlite")
cur = conn.cursor()

cur.execute(""" CREATE TABLE IF NOT EXISTS Categories(
    id INTEGER NOT NULL UNIQUE,
    name TEXT UNIQUE,
    categoryLink TEXT,
    totalIndex INTEGER,
    currentIndex INTEGER,
    PRIMARY KEY(id AUTOINCREMENT)
)
""")
cur.execute(""" CREATE TABLE IF NOT EXISTS Search(
    id INTEGER NOT NULL UNIQUE,
    pageTotal INTEGER,
    pageCurrent INTEGER,
    PRIMARY KEY(id AUTOINCREMENT)
    )
""")
cur.execute(""" CREATE TABLE IF NOT EXISTS Games(
    id INTEGER NOT NULL UNIQUE,
    steamId INTEGER UNIQUE,
    name TEXT,
    pageLink TEXT,
    infoGathered INTEGER,
    PRIMARY KEY(id AUTOINCREMENT)
)
""")

cur.execute("""CREATE TABLE IF NOT EXISTS GameDetails(
    id INTEGER NOT NULL UNIQUE,
    gameId INTEGER,
    popularTags TEXT,
    price TEXT,
    features TEXT,
    lanInterface TEXT,
    LanAudio TEXT,
    lanSubtitle TEXT,
    lanAllSupported INTEGER,
    genre TEXT,
    developer TEXT,
    publisher TEXT,
    releaseDate TEXT,
    minSysReq TEXT,
    recSysReq TEXT,
    reviewTotal INTEGER,
    reviewPositive INTEGER,
    reviewNegative INTEGER,
    PRIMARY KEY(id AUTOINCREMENT))
""")

conn.commit()


def gatherGames():
    cur.execute("""SELECT * FROM Search ORDER BY pageCurrent DESC LIMIT 1""")
    row = cur.fetchone()
    pageList = list()
    #------------------------------ if table is empty retrive max page data and insert
    if row is None:
        url = "https://store.steampowered.com/search/?ignore_preferences=1&category1=998&page=1&ndl=1"
        response = urlopen(url=url)
        soup = BeautifulSoup(response.read(), "html.parser")
        pages = soup.find_all("a", onclick= lambda onclick: onclick and "SearchLink" in onclick, class_= lambda class_: class_ != "pagebtn")
        for page in pages:
            number = int(page.text.strip())
            pageList.append(number)
        maxPage = max(pageList)
        cur.execute("""INSERT INTO Search(pageTotal, pageCurrent) VALUES(?,1)""", (maxPage,))
        conn.commit()
        cur.execute("""SELECT * FROM Search ORDER BY pageCurrent DESC LIMIT 1""")
        row = cur.fetchone()
    #------------------ after insert start retriving game names,links starting from current page
    cPage = int(row[2])
    tPage = int(row[1])
    print(f"Current Page {cPage}, Total Page {tPage}")
    many = int(input("How many page do you want to retrive?: "))
    count = 0
    while cPage < tPage and many > 0:
        try:
            url = f"https://store.steampowered.com/search/?ignore_preferences=1&category1=998&page={cPage}&ndl=1"
            response = urlopen(url=url)
            soup = BeautifulSoup(response.read(), "html.parser")
            links = soup.find_all("a", href= lambda href: href and "https://store.steampowered.com/app/" in href)
            for link in links:
                gLink = link["href"]
                title = link.find("span", class_="title").text.strip()
                appIndex = gLink.find("app/") + 4
                a = gLink[appIndex:]
                sId = int(a[:a.find("/")])

                cur.execute("""INSERT OR IGNORE INTO Games(steamId, name, pageLink, infoGathered) VALUES(?,?,?,0)""",(sId, title, gLink))

                conn.commit()
                count = count + 1
                print(f"{count}) Inserted: {title}")

            #update Search table
            many = many - 1
            print(f"Page {cPage} retrived")
            cPage = cPage + 1
            cur.execute("""UPDATE Search SET pageCurrent =? WHERE pageCurrent=?""",(cPage, cPage-1))
            conn.commit()
            print(f"{count} records inserted to the database succesfully")
            #wait for 3 seconds, not want to occupai steam servers
            print("Waiting 0.5 seconds for next page...")
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("Stopped by User...")
            break
        except Exception as e:
            print("Error: " + str(e))
            print("Program Terminated!")
            break


def gatherGameInfo():
    cur.execute("""SELECT * FROM Games WHERE infoGathered = 0 ORDER BY RANDOM() LIMIT 1""")
    #cur.execute("""SELECT * FROM Games WHERE steamId = 202970""")
    row = cur.fetchone()
    if row is None:
        print("No game data exists or all game links has been retrived.")
        print("Try to Retrive Game Links.")
        print("Program Terminated")
        quit()
    else:
        try:
            print(f"Selected Game: {row[2]} \n Starting Data Retrieving Process in 0.4 seconds...")
            time.sleep(0.4)
            url = row[3]
            response = urlopen(url=url)
            soup = BeautifulSoup(response.read(), "html.parser")

            # First find popular user defined tags-----
            popularTags = ""
            pTags = soup.find_all("a", class_="app_tag")
            for tag in pTags:
                text = tag.text.strip()
                popularTags = popularTags + text + ","
            popularTags = popularTags[:-1]
            #-------------------------------------------
            # Reviews total - positive - negative ------
            totalRev = int(soup.find("label", attrs={"for":"review_type_all"}).find("span").text[1:-1].replace(",",""))
            positiveRev = int(soup.find("label", attrs={"for":"review_type_positive"}).find("span").text[1:-1].replace(",",""))
            negativeRev = int(soup.find("label", attrs={"for":"review_type_negative"}).find("span").text[1:-1].replace(",",""))
            #--------------------------------------------
            #System Requirements Min and Recommended-----
            minSys = ""
            minDiv = soup.find("div", class_="game_area_sys_req_leftCol")
            recSys = ""
            recDiv = soup.find("div", class_="game_area_sys_req_rightCol")
            sys = ""
            if minDiv is not None and recDiv is not None:
                minLiElements = minDiv.find_all("li")
                recLiElements = recDiv.find_all("li")
                for li in minLiElements:
                    minSys = minSys + li.text + ","
                minSys = minSys[:-1]

                for li in recLiElements:
                    recSys = recSys + li.text + ","
                recSys = recSys[:-1]
            else:
                sysDiv = soup.find("div", class_="game_area_sys_req_full")
                sysLiElements = sysDiv.find_all("li")
                for li in sysLiElements:
                    sys = sys + li.text + ","
                sys = sys[:-1]
            #---------------------------------------------
            # Genre, developer, publisher ----------------
            infoBlock = soup.find("div", id="genresAndManufacturer")

            genreLinks = infoBlock.find_all("a", href= lambda href: href and "genre" in href)
            genre = ""
            for link in genreLinks:
                genre = genre + link.text.strip() + ","
            genre = genre[:-1]

            developerLinks = infoBlock.find_all("a", href= lambda href: href and "developer" in href)
            developer = ""
            for link in developerLinks:
                developer = developer + link.text.strip() + ","
            developer = developer[:-1]

            publisherLinks = infoBlock.find_all("a", href= lambda href: href and "publisher" in href)
            publisher = ""
            for link in publisherLinks:
                publisher = publisher + link.text.strip() + ","
            publisher = publisher[:-1]
            #---------------------------------------------
            # Release Date -------------------------------
            releaseDate = soup.find("div", class_="date").text
            #--------------------------------------------
            # Features ----------------------------------
            fDivs = soup.find_all("div", class_="label")
            features = ""
            for ft in fDivs:
                features = features + ft.text.strip() + ","
            #--------------------------------------------
            # Price -------------------------------------
            priceBlocks = soup.find_all("div", class_="game_purchase_action_bg")
            for div in priceBlocks:
                price = None
                priDiv = div.find("div", class_="game_purchase_price price")
                #if priDiv is not None: price = priDiv.text.strip()
                if priDiv is None:
                    priDiv = div.find("div", class_="discount_original_price")
                    if priDiv is None: continue
                    else:
                        price = priDiv.text.strip()
                        break
                else:
                    price = priDiv.text.strip()
                    break

            #---------------------------------------------
            # Languages, Interface, Audio, Subtitle ------
            lanInterface = ""
            lanAuido = ""
            lanSubtitle = ""
            lanAllSupported = 0
            tableDiv = soup.find("div", id="languageTable")

            tableRows = tableDiv.find_all("tr")[1:]
            lanAllSupported = len(tableRows)
            for tr in tableRows:
                tds = tr.find_all("td")
                lname = tds[0].text.strip()
                interCheck = tds[1].text.strip()
                auidoCheck = tds[2].text.strip()
                subtCheck = tds[3].text.strip()
                if interCheck != "": lanInterface = lanInterface + lname + ","
                if auidoCheck != "": lanAuido = lanAuido + lname + ","
                if subtCheck != "": lanSubtitle = lanSubtitle + lname + ","
            lanInterface = lanInterface[:-1]
            lanAuido = lanAuido[:-1]
            lanSubtitle = lanSubtitle[:-1]
            #------------------------------------------------------------
            print("All Data Retrieved Succesfully \n Inserting to the database...")

            # Database insert section------------------------------------
            cur.execute("""INSERT INTO GameDetails(
                gameId, popularTags, price, features, lanInterface, lanAudio, lanSubtitle, lanAllSupported, genre, developer, publisher, releaseDate, minSysReq, recSysReq, reviewTotal, reviewPositive, reviewNegative)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(row[0],popularTags,price, features, lanInterface, lanAuido, lanSubtitle, lanAllSupported, genre, developer, publisher, releaseDate, minSys, recSys, totalRev, positiveRev, negativeRev))

            cur.execute("""UPDATE Games SET infoGathered = ? WHERE id = ?""",(1, row[0]))

            conn.commit()
            print("Database Insertation Comleted.")
            print("-------------------------------------------")

        except Exception as e:
            print(e)
            print(row[2] + ": Game Data Could Not Retrieved! ")
            print("----------------Error-------------------------------")

select = input("Gather Game links enter 1 - Gather game Details enter 2: ")
if select == "1":
    gatherGames()
elif select == "2":
    many = int(input("How many game data do you want to retrieve?: "))
    if many == "": many = 0
    for i in range(many):
        gatherGameInfo()


#Gather All Categories from steam and insert into database
def gatherCategory():
    cur.execute("select * from Categories")
    rows = cur.fetchall()
    if rows is None:
        url = "https://store.steampowered.com/"
        response = urlopen(url=url)
        soup = BeautifulSoup(response.read(), "html.parser")

        #find all a tags which inculudes category links
        categories = soup.find_all("a", href= lambda href: href and "https://store.steampowered.com/category" in href)

        for category in categories:
            name = category.text.strip()
            #print(category.text, " = ", category["href"])
            cur.execute(""" INSERT OR IGNORE INTO Categories(name, categoryLink, totalIndex, currentIndex) values(?, ?, 0, 0)
            """, (name, category["href"]))
        conn.commit()

conn.close()