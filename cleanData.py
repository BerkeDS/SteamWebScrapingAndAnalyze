import sqlite3

conn = sqlite3.connect("SteamDB.sqlite")
cur = conn.cursor()

#cur.execute("SELECT name, popularTags, price, features, lanInterface, LanAudio, lanSubtitle, lanAllSupported, genre, developer, publisher, releaseDate, minSysReq, recSysReq, reviewTotal, reviewPositive, reviewNegative, reviewPercentage from GameDetails JOIN Games ON GameDetails.gameId=Games.id order by GameDetails.gameId")

cur.execute("UPDATE GameDetails SET reviewPercentage = (reviewPositive*100)/reviewTotal")

#cur.execute("DELETE From GameDetails where reviewTotal < 100")

conn.commit()
conn.close()


