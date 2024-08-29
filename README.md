# Lazer Bracket Generator

This application contains a script that writes a bracket.json file for your lazer tourney client. To get started just download this repository by clicking the flashy "code" button to the top right of github, download ZIP, extract the files and open 'lazer_bracket_generator.exe' on your computer. 

You might need to give the script permission to run before it can open, but after that you should see the clint open. Set in the appropriate settings for your tournament, scroll down and press "execute script".

Once the script is done you should see a bracket.json file in the folder with the exe.

The script checks for scuffed qualifier lobbies. If a player disconnected mid match or something else went wrong, a dialogue will pop up where you can correct anything needed.

## Settings

### API

To request the data you need to have an API key. If you have never used the osu!api before you can get one in your osu! account settings page under the OAuth section. Write a random name and a random URL e.g: “http://localhost:XXXX/” where you replace “XXXX” with a random 4 digit number greater than 1024. Here you will get your client ID and client secret.

### Rounds

Are you hosting ro16 or ro32 or smth else.. The script supports tourneys of between 4 and 128 players.

### IDs

Here you need to write in the match IDs of all the qualifier lobbies. You find the ID at the back of the mp link "https://osu.ppy.sh/community/matches/XXXXXXXXX".

Keep in mind the first qualifier lobby you input (top left) is used to determine the mappool, so make sure this lobby is conducted correctly with no players disconnecting mid play or other strange events.

### settings

Check the single elimination if you don't want a loser bracket.

The redemption bracket is for creating a seperate bracket for the people that did not qualify. You will need to specify how many players you want in redemption. If all remaining players should play redemption, just write a big number (no bigger than 128)

The manual input is in case a qualifier lobby has been conducted badly, you can manually input the scores of the missing players.

### TeamVS

Check this box if you are running a teams tournament. After clicking, a text box will appear. Here you need to write all the participating teams. I use the same format as for screening. This is comma or tab separated name, team and ID e.g.

mrekk,almond,7562902
Accolibed,almond,9269034
lifeline,walnut,11367222
gnahus,walnut,12779141

Be aware some foreign characters are not allowed in the team names. Commas are also not allowed.

### Seeding method

Which method are you using for determining the seeds? 

Total score just sums up the score from all maps, highest total score gets highest seed.

Average rank takes the rank of a player on each map and calculates the average across the pool.

Zipf's law uses the formula 100/(map placement + mappool size * 1.4).

## Finally

While the "Remember" box is checked, your settings will be saved after you close the client. 

If something is wrong and you wish to terminate the script, click the "Terminate script" button. Although you'll need to close any pop ups before the script terminates. 

Besides a bracket.json file there will also be a folder with extra data. These files are formattet to be copy pasted into your google sheets if you need

My projects are open source. If you are interrested in the backend of my work, you can see everything in the attached python file. Other wise you are very welcome to contact me on discord with any questions.