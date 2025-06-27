# ghost-vhs
_analogue-slop meets Instagram DM MCP_

### what is it?
 > a two-part experiment for the @galalabs instagram-dm hackathon.  
 > vhs glitch edited with your username & a mysterious message tags you in public, slides into your dms, then lures you to a "terminal" at **ghost-vhs.com**.

### parts
1. **ghost-mcp-server**  
 > pulls targets from brightdata  
 > auto-cuts personalised VHS clips  
 > uploads reel + tag & DM with `ghost-vhs.com/<username>`  
 > utilises a rotating account pool with proxies  
 > running locally on nvidia jetson nano dev kit
2. **ghost-vhs.com**  
 > shows your IG stats with a countdown & email collection form  
 > transitions into an endless feed of vhs clips  
 > cloudflare workers - edge hosted

### why  
 > fight ai slop with vhs slop, celebrate using the technology & internet for creative expression, fun intro to mcp, take part in a hackathon for the first time

### any "actual" use?   
 > with the smallest amount of creativity this could be used to market a product or service 
 
### example usage
 > deploy a campagin subagents for  10 random users, create personalized videos for each and dm it to them with a custom urll.
 > personalize a video for user @username, dm it to them with a silly message.  
 > create, list, delete campaigns  
 > create a dataset based on "target user description" with 50 lines  

### quick start
```bash
# Clone and setup
git clone <repository-url>
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

