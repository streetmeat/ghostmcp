# vhs-ghost
_analogue-slop meets Instagram DM MCP_

https://github.com/user-attachments/assets/f5c1f086-9c24-4bb3-af58-8adb2724d305


<details>
 
<summary>More demo videos</summary>
 
<br>
 
https://github.com/user-attachments/assets/ce39b008-b0ba-45dc-b59b-32e5ce76ac0b

 https://github.com/user-attachments/assets/ebea8689-97a5-427e-9724-8380125a8bed

</details>

### what is it?
 > a two-part experiment for the @galalabs instagram-dm hackathon.  
 > vhs clips are edited with your username & a mysterious message tags you in public, slides into your dms, then lures you to a "terminal" at a custom domain [vhs-ghost.com/username](https://vhs-ghost.com/username)

### parts
1. **ghost-mcp-server**  
 > pulls targets from brightdata  
 > auto-cuts personalised VHS clips  
 > uploads reel, tags and DMs user with [`vhs-ghost.com/<username>`](https://vhs-ghost.com/)  
 > utilises a rotating account pool with proxies  
 > running locally on nvidia jetson nano dev kit

2. **[vhs-ghost.com](https://vhs-ghost.com/)**  
 > the custom url shows the user their IG stats, email collection & mysterious countdown  
 > transitions into an endless feed of vhs clips  
 > cloudflare workers - edge hosted

### why  
 > fight ai slop with vhs slop  
 > celebrate using technology & the internet for creative expression  
 > opportunity to get introduced to mcp and hackathons   

### any "actual" use?   
 > could be pivotd to market a product or service  
 > my theory is that combing an obscure vhs clip, editing the actual username, and sending a url with /username it will create enough intrigue for some click through  
 
### example usage
 > create a campaign with 10 random users, use the use the campaign video tool to create personalized videos, then deploy subagents to upload and dm in parallel. 
 > personalize a video for @username, dm it to them with a silly message.  
 > list all campaigns, delete x campaign, create a campgain. 
 > create a dataset of people with between 100-1000 followers and follow #nostalgia with a limit of 50 lines. Check every minute for the dataset until it is delievered, dont do anything else. 

### quick start
```bash
# Clone and setup
git clone https://github.com/streetmeat/ghostmcp.git
cd ghost

# Configure
cd ghost_mcp
cp .env.example .env
cp accounts.json.example accounts.json
# Edit these files with your credentials

# Install and run
pip install -r requirements.txt
python src/mcp_server.py --use-account-pool
```

### mcp tools
**Campaign Management:**
- `mcp__ghost__fetch_bright_data_users` - Get users from Bright Dataset Marketplace API
- `mcp__ghost__download_bright_data_snapshot` - Download completed snapshot
- `mcp__ghost__select_random_users` - Select random users from datasets
- `mcp__ghost__create_campaign` - Create new campaign
- `mcp__ghost__get_campaign_status` - Check campaign progress
- `mcp__ghost__delete_campaigns` - Delete campaigns
- `mcp__ghost__prepare_campaign_videos` - Pre-personalize videos

**Video Processing:**
- `mcp__ghost__create_video_chunks` - Create base video chunks
- `mcp__ghost__list_video_chunks` - List available chunks
- `mcp__ghost__get_chunk_info` - Get chunk details
- `mcp__ghost__personalize_specific_chunk` - Add username overlay

**Instagram Operations:**
- `mcp__ghost__send_message` - Send DM message
- `mcp__ghost__upload_video_post` - Upload reel with tag
- `mcp__ghost__share_post_to_dm` - Share post to DM
- `mcp__ghost__get_user_info` - Get user information
- `mcp__ghost__get_user_posts` - Get user's posts
- `mcp__ghost__get_account_status` - Check account pool status
- `mcp__ghost__mark_operation_complete` - Trigger account cooldown

### ideas to extend
 > fix all the issues and complexity that ideating & making this in 48 hours with claude created  
 > troubleshoot speed of several tools  
 > add analytics  
 > add a database  
 > dynamic url creation  
 > extended video editing  
 > make swipe feel better  
 > figure out how to beat the algorithm  
 > implement unique fingerprinting  
 > figure out some way to pay for the claude subscription with it ;) 

### detailed setup & docs
- [MCP Server Documentation](ghost_mcp/README.md) - Complete setup and API reference

**there's some weird decisions due to the jetson's quirks and my lack of knowledge**  
**don't trust the code.**
**yes the mcp_server.py is 2k lines ><**
