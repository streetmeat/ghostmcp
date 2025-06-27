/**
 * Ghost Media Haunting Bot - Cloudflare Worker
 * With glitchy video transition after 45 seconds
 * v3 - Video transitions
 */

// Sanitize username to prevent XSS attacks
function sanitizeUsername(username) {
  // Remove any HTML/script tags and dangerous characters
  return username
    .replace(/[<>'"]/g, '') // Remove HTML-sensitive chars
    .replace(/[^\w\-_.]/g, '') // Keep only safe characters
    .substring(0, 50); // Limit length
}

// Escape username for safe HTML rendering
function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
}

// Shared constants to eliminate duplication
const SHARED_ASSETS = {
  ASCII_ART: `
   ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗
  ██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝
  ██║  ███╗███████║██║   ██║███████╗   ██║   
  ██║   ██║██╔══██║██║   ██║╚════██║   ██║   
  ╚██████╔╝██║  ██║╚██████╔╝███████║   ██║   
   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝`,
  TAGLINE: 'THE SIGNAL FINDS EVERYONE',
  VHS_GHOST_SPAN: '<span class="typing glitch" data-text="VHS GHOST">VHS GHOST</span>',
  SCAN_LINES: '<div class="scanlines"></div>'
};

// Template functions to reduce duplication
function createTerminalHTML(content, includeVideoContainer = true) {
  return `
    <div class="terminal">
        ${SHARED_ASSETS.SCAN_LINES}
        
        <!-- Terminal content -->
        <div class="terminal-content">
            ${content}
        </div>
    </div>
    ${includeVideoContainer ? `
    <div id="video-loop-container" class="video-loop-container">
        <video id="video-a" class="loop-video active" playsinline></video>
        <video id="video-b" class="loop-video" playsinline></video>
        <button id="mute-toggle" class="mute-button unmuted"></button>
        <div class="swipe-indicator">SWIPE ↕</div>
    </div>` : ''}
    <div class="static-transition"></div>
  `;
}

// Consolidated countdown timer function
function createCountdownTimer(element, duration, options = {}) {
  const {
    prefix = '> ',
    suffix = '',
    onComplete = null,
    onTick = null,
    blinkAt = 5,
    dangerColor = '#ff0000',
    normalStyle = 'font-weight: normal;'
  } = options;
  
  let timeLeft = duration;
  
  const updateTimer = () => {
    if (timeLeft >= 0) {
      // Update display
      element.innerHTML = `${prefix}<span style="${normalStyle}">${timeLeft}</span>${suffix}`;
      
      // Apply danger styles if needed
      if (timeLeft <= blinkAt && timeLeft > 0) {
        element.style.animation = 'blink 0.5s infinite';
        if (timeLeft <= 3) {
          element.style.color = dangerColor;
        }
      }
      
      // Call tick callback if provided
      if (onTick) onTick(timeLeft);
      
      if (timeLeft === 0) {
        // Timer complete
        if (onComplete) onComplete();
      } else {
        timeLeft--;
        setTimeout(updateTimer, 1000);
      }
    }
  };
  
  // Start the timer
  updateTimer();
  
  // Return control object
  return {
    stop: () => { timeLeft = -1; },
    getTimeLeft: () => timeLeft
  };
}

// Get user data inside function to avoid global exposure
function getUserData(username) {
  // Generate a timestamp from 5-30 minutes ago for realism
  const minutesAgo = Math.floor(Math.random() * 25) + 5;
  const timestamp = new Date(Date.now() - (minutesAgo * 60 * 1000)).toISOString();
  
  const data = {
    "testuser1": {
      "username": "testuser1",
      "user_id": "1234567",
      "followers": 1500,
      "following": 1200,
      "posts_count": 450,
      "avg_engagement": 0.0850,
      "video_sent": "CHUNK_001",
      "sent_at": timestamp,
      "clicked": false
    },
    "demouser": {
      "username": "demouser",
      "user_id": "9876543",
      "followers": 2300,
      "following": 890,
      "posts_count": 230,
      "avg_engagement": 0.1250,
      "video_sent": "CHUNK_003",
      "sent_at": timestamp,
      "clicked": false
    },
    "hackathon": {
      "username": "hackathon",
      "user_id": "5555555",
      "followers": 999,
      "following": 666,
      "posts_count": 333,
      "avg_engagement": 0.0999,
      "video_sent": "CHUNK_005",
      "sent_at": timestamp,
      "clicked": false
    }
  };
  return data[username] || null;
}

// Complete CSS matching Flask version + video transitions
const TERMINAL_CSS = `
/* Terminal base styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

html, body {
    width: 100%;
    height: 100%;
    overflow: hidden;
}

body {
    background: #0a0a0a;
    color: #00ff00;
    font-family: 'Courier New', Courier, monospace;
    font-size: 14px;
    line-height: 1.6;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
}

.terminal {
    position: relative;
    height: 100vh;
    padding: 20px;
    background: radial-gradient(ellipse at center, #0a0a0a 0%, #000000 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
}

/* CRT screen effect */
.terminal::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(ellipse at center, transparent 0%, rgba(0, 255, 0, 0.1) 100%);
    pointer-events: none;
}

/* Scan lines */
.scanlines {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(
        transparent 50%,
        rgba(0, 255, 0, 0.03) 50%
    );
    background-size: 100% 4px;
    animation: scan 8s linear infinite;
    pointer-events: none;
    z-index: 1;
}

@keyframes scan {
    0% { transform: translateY(0); }
    100% { transform: translateY(10px); }
}

/* Terminal content */
.terminal-content {
    position: relative;
    max-width: 800px;
    margin: 0 auto;
    z-index: 2;
}

/* Text effects */
.header {
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 30px;
    text-shadow: 0 0 10px #00ff00;
}

.line {
    margin: 8px 0;
    min-height: 1.6em;
}

.data-readout .line:last-child {
    margin-bottom: 0;
}

/* Terminal cursor for typing effect */
.typing-line::after {
    content: '█';
    animation: blink 1s infinite;
    color: #00ff00;
}

/* Highlight styles */
.highlight {
    color: #00ff00;
    font-weight: bold;
    text-shadow: 0 0 5px #00ff00;
}

.success {
    color: #00ff00;
}

.redacted {
    background: #00ff00;
    color: #0a0a0a;
    padding: 0 4px;
    font-weight: bold;
}

.filename {
    color: #00ffff;
}

/* Access section */
.access-section {
    margin-top: 0;
    opacity: 0;
    transition: opacity 0.5s ease-in;
    cursor: text;
}

.prompt {
    display: flex;
    align-items: center;
    font-size: 14px;
    font-weight: normal;
    padding: 10px 0;
    cursor: text;
}

.input-wrapper {
    position: relative;
    display: inline-flex;
    align-items: center;
}

.terminal-input {
    background: transparent;
    border: none;
    color: #00ff00;
    font-family: inherit;
    font-size: 14px;
    font-weight: normal;
    outline: none;
    padding-left: 0;
    padding-right: 15px;
    text-shadow: 0 0 5px #00ff00;
    caret-color: transparent;
    width: auto;
    max-width: 400px;
}

/* Block cursor span */
.block-cursor {
    position: absolute;
    display: inline-block;
    width: 10px;
    height: 1.2em;
    background-color: #00ff00;
    animation: blink 1s infinite;
    box-shadow: 0 0 5px #00ff00;
    pointer-events: none;
    left: 0;
}

/* Terminal cursor blink animation */
@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}

/* Response message */
#response-message {
    margin-top: 20px;
    font-weight: bold;
    text-shadow: 0 0 10px currentColor;
}

#response-message.success {
    color: #00ff00;
}

#response-message.error {
    color: #ff0000;
}

.hidden {
    display: none;
}


/* Glitch effect */
.glitch {
    position: relative;
}

.glitch::before,
.glitch::after {
    content: attr(data-text);
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
}

.glitch::before {
    color: #00ffff;
    z-index: -1;
    transform: translate(2px, -1px);
}

.glitch::after {
    color: #ff00ff;
    z-index: -2;
    transform: translate(-2px, 1px);
}

/* Video transition styles */
.video-loop-container {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: #000;
    z-index: 9999;
    opacity: 0;
    pointer-events: none;
    display: flex;
    align-items: center;
    justify-content: center;
}

.video-loop-container.visible {
    opacity: 1;
    pointer-events: all;
}

.loop-video {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 100%;
    height: 100%;
    object-fit: contain;
    opacity: 0;
    transition: opacity 0.5s ease-in-out;
}


/* Swipe indicator for mobile */
.swipe-indicator {
    position: absolute;
    bottom: 100px;
    left: 50%;
    transform: translateX(-50%);
    color: rgba(0, 255, 0, 0.8);
    font-family: 'Courier New', monospace;
    font-size: 18px;
    font-weight: bold;
    text-align: center;
    z-index: 10002;
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
    text-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
    letter-spacing: 2px;
}

.swipe-indicator.visible {
    opacity: 1;
}

@media (min-width: 768px) {
    .swipe-indicator {
        display: none;
    }
}


/* Video sliding transition */
.loop-video.slide-up {
    animation: slideUp 0.4s ease-out forwards;
}

.loop-video.slide-down {
    animation: slideDown 0.4s ease-out forwards;
}

@keyframes slideUp {
    0% {
        transform: translate(-50%, -50%);
        opacity: 1;
    }
    100% {
        transform: translate(-50%, -150%);
        opacity: 0;
    }
}

@keyframes slideDown {
    0% {
        transform: translate(-50%, -50%);
        opacity: 1;
    }
    100% {
        transform: translate(-50%, 50%);
        opacity: 0;
    }
}

.loop-video.slide-in-up {
    animation: slideInUp 0.4s ease-out forwards;
}

.loop-video.slide-in-down {
    animation: slideInDown 0.4s ease-out forwards;
}

@keyframes slideInUp {
    0% {
        transform: translate(-50%, 50%);
        opacity: 0;
    }
    100% {
        transform: translate(-50%, -50%);
        opacity: 1;
    }
}

@keyframes slideInDown {
    0% {
        transform: translate(-50%, -150%);
        opacity: 0;
    }
    100% {
        transform: translate(-50%, -50%);
        opacity: 1;
    }
}

/* For landscape/desktop screens, limit max width to maintain 9:16 aspect */
@media (min-aspect-ratio: 16/9) {
    .loop-video {
        max-width: calc(100vh * 9 / 16);
        width: auto;
        height: 100%;
    }
}

/* For very wide screens, ensure video doesn't get too small */
@media (min-aspect-ratio: 21/9) {
    .loop-video {
        max-width: calc(100vh * 9 / 16);
        min-width: 50vw;
    }
}

.loop-video.active {
    opacity: 1;
}

.loop-video::-webkit-media-controls {
    display: none !important;
}

/* Static transition overlay */
.static-transition {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 10000;
    pointer-events: none;
    opacity: 0;
    background: #111;
}

.static-transition::before {
    content: "";
    position: absolute;
    top: -100%;
    left: -100%;
    width: 300%;
    height: 300%;
    background: repeating-linear-gradient(
        0deg,
        #000 0%,
        #000 50%,
        #fff 50%,
        #fff 100%
    );
    background-size: 4px 4px;
    animation: static-move 0.05s steps(5) infinite;
    opacity: 0.5;
    mix-blend-mode: difference;
}

@keyframes static-move {
    0% { transform: translate(0, 0); }
    100% { transform: translate(10px, 10px); }
}

/* Static flash animation */
@keyframes static-flash {
    0% { 
        opacity: 0; 
    }
    10% { 
        opacity: 1; 
    }
    90% { 
        opacity: 1; 
    }
    100% { 
        opacity: 0; 
    }
}

.static-transition.active {
    animation: static-flash 120ms linear forwards;
}

/* Mute/unmute button */
.mute-button {
    position: absolute;
    bottom: 20px;
    right: 20px;
    width: 40px;
    height: 40px;
    background: rgba(0, 0, 0, 0.8);
    border: 1px solid #00ff00;
    color: #00ff00;
    font-family: 'Courier New', monospace;
    font-size: 18px;
    cursor: pointer;
    z-index: 10001;
    display: none;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
    border-radius: 4px;
}

/* Desktop positioning - place button next to video */
@media (min-width: 768px) and (min-aspect-ratio: 16/9) {
    .mute-button {
        /* Position at fixed distance from center */
        /* Video width is 100vh * 9/16 = 56.25vh */
        /* Half of that is 28.125vh */
        /* Add padding of 20px */
        position: absolute;
        left: calc(50% + 28.125vh + 20px);
        top: 50%;
        transform: translateY(-50%);
        right: auto;
        bottom: auto;
    }
}

/* For portrait or square screens on desktop */
@media (min-width: 768px) and (max-aspect-ratio: 16/9) {
    .mute-button {
        /* On narrower screens, position in top right */
        position: absolute;
        top: 20px;
        right: 20px;
        left: auto;
        bottom: auto;
        transform: none;
    }
}

/* For portrait/narrow screens, keep button in corner */
@media (max-aspect-ratio: 9/16) {
    .mute-button {
        position: absolute;
        bottom: 20px;
        right: 20px;
        left: auto;
        top: auto;
        transform: none;
    }
}

/* Mobile positioning remains fixed to viewport */
@media (max-width: 767px) {
    .mute-button {
        position: fixed;
        bottom: 20px;
        right: 20px;
        /* Ensure background is always visible on mobile */
        background: rgba(0, 0, 0, 0.8) !important;
    }
}

/* Only apply hover effects on devices that support hover (not touch devices) */
@media (hover: hover) {
    .mute-button:hover {
        background: rgba(0, 0, 0, 0.9);
        box-shadow: 0 0 20px #00ff00;
        border-color: #00ff00;
    }
}

/* Ensure background persists after touch on mobile */
.mute-button:active {
    background: rgba(0, 0, 0, 0.8);
}

.mute-button.visible {
    display: flex;
}

.mute-button.muted::after {
    content: '🔇';
}

.mute-button.unmuted::after {
    content: '🔊';
}

/* Glitch transition effects */
@keyframes glitch-anim-1 {
    0% { clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%); }
    5% { clip-path: polygon(0 20%, 100% 20%, 100% 40%, 0 40%); }
    10% { clip-path: polygon(0 60%, 100% 60%, 100% 80%, 0 80%); }
    15% { clip-path: polygon(0 10%, 100% 10%, 100% 90%, 0 90%); }
    20% { clip-path: polygon(0 30%, 100% 30%, 100% 70%, 0 70%); }
    25% { clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%); }
    100% { clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%); }
}

@keyframes glitch-anim-2 {
    0% { transform: translate(0); }
    20% { transform: translate(-2px, 2px); }
    40% { transform: translate(-2px, -2px); }
    60% { transform: translate(2px, 2px); }
    80% { transform: translate(2px, -2px); }
    100% { transform: translate(0); }
}

@keyframes flash-white {
    0%, 40% { background: transparent; }
    50% { background: #fff; }
    60%, 100% { background: transparent; }
}

@keyframes rgb-shift {
    0% { filter: none; }
    20% { filter: hue-rotate(90deg) saturate(2); }
    40% { filter: hue-rotate(180deg) saturate(2); }
    60% { filter: hue-rotate(270deg) saturate(2); }
    80% { filter: hue-rotate(360deg) saturate(2); }
    100% { filter: none; }
}

@keyframes static-noise {
    0%, 100% { opacity: 0; }
    10%, 90% { opacity: 0.2; }
    20%, 80% { opacity: 0.4; }
    30%, 70% { opacity: 0.6; }
    40%, 60% { opacity: 0.8; }
    50% { opacity: 1; }
}

.terminal.glitching {
    animation: 
        glitch-anim-1 0.8s steps(1) forwards,
        glitch-anim-2 0.3s infinite,
        rgb-shift 0.8s steps(1);
}

.terminal.glitching::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: repeating-linear-gradient(
        0deg,
        rgba(255,255,255,0.03) 0px,
        transparent 1px,
        transparent 2px,
        rgba(255,255,255,0.03) 3px
    );
    animation: glitch-anim-2 0.2s infinite;
    pointer-events: none;
    z-index: 1;
}

.terminal.glitching::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: 
        repeating-linear-gradient(
            90deg,
            transparent 0,
            rgba(255,0,0,0.1) 2px,
            transparent 4px
        ),
        repeating-linear-gradient(
            0deg,
            transparent 0,
            rgba(0,255,0,0.1) 2px,
            transparent 4px
        );
    animation: static-noise 0.8s steps(1);
    mix-blend-mode: multiply;
    pointer-events: none;
    z-index: 2;
}

.flash-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: #fff;
    opacity: 0;
    pointer-events: none;
    z-index: 10000;
}

.flash-overlay.flashing {
    animation: flash-white 0.8s ease-out forwards;
}

/* Static subtle glow for countdown and email prompt */
.countdown-text,
.countdown-line {
    text-shadow: 0 0 5px #00ff00;
}

.email-prompt {
    text-shadow: 0 0 5px #00ffff;
}

/* Mobile responsive */
@media (max-width: 600px) {
    body {
        font-size: 12px;
    }
    
    .terminal {
        padding: 15px;
        height: 100vh;
        height: 100dvh; /* Dynamic viewport height for mobile */
    }
    
    .terminal-content {
        padding: 0 10px;
        width: 100%;
        max-width: 100%;
    }
    
    .header {
        font-size: 20px;
    }
    
    /* Email prompt on its own line */
    .prompt {
        flex-direction: column;
        align-items: flex-start;
    }
    
    .prompt > span:first-child {
        margin-bottom: 10px;
    }
    
    .input-wrapper {
        width: 100%;
    }
    
    .terminal-input {
        width: 100%;
        max-width: none;
    }
    
    /* Prevent any overflow */
    * {
        max-width: 100%;
    }
    
    .data-readout {
        overflow-wrap: break-word;
        word-wrap: break-word;
    }
}
`;

// Video transition JavaScript
const VIDEO_TRANSITION_JS = `
// Video transition system for Ghost Media
(function() {
    // Configuration
    const TRANSITION_DELAY = 30000; // 30 seconds
    const GLITCH_DURATION = 800; // 0.8 second glitch
    const VIDEO_BASE_URL = '/api/video'; // Serve videos through Worker
    
    // Countdown timer
    let countdownInterval;
    let timeRemaining = 30;
    
    // Fetch video chunks dynamically from R2
    async function getVideoChunks() {
        try {
            const response = await fetch('/api/chunks');
            const data = await response.json();
            return data.chunks && data.chunks.length > 0 ? data.chunks : [
                // Fallback chunks if API fails
                'chunk_0260d22e.mp4',
                'chunk_04bf9e4e.mp4',
                'chunk_0b42128c.mp4',
                'chunk_117f3181.mp4',
                'chunk_14c04eaf.mp4'
            ];
        } catch (error) {
            console.error('Error fetching chunks:', error);
            // Fallback to some default chunks
            return [
                'chunk_0260d22e.mp4',
                'chunk_04bf9e4e.mp4',
                'chunk_0b42128c.mp4',
                'chunk_117f3181.mp4',
                'chunk_14c04eaf.mp4'
            ];
        }
    }
    
    let videoChunks = [];
    let currentVideoIndex = 0;
    let videoA, videoB;
    let currentVideo = 'A';
    let preloadQueue = [];
    let controlsTimeout = null;
    let isNavigating = false;
    let navigationTimeout = null;
    
    // Initialize video queue by fetching chunks
    async function initializeVideoQueue() {
        videoChunks = await getVideoChunks();
        const shuffledVideos = shuffle(videoChunks);
        preloadQueue = shuffledVideos;
        preloadNextVideo();
    }
    
    // Shuffle array
    function shuffle(array) {
        const arr = [...array];
        for (let i = arr.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [arr[i], arr[j]] = [arr[j], arr[i]];
        }
        return arr;
    }
    
    // Create video player container
    function createVideoContainer() {
        const container = document.createElement('div');
        container.id = 'video-loop-container';
        container.className = 'video-loop-container';
        container.innerHTML = \`
            <video id="video-a" class="loop-video active" playsinline></video>
            <video id="video-b" class="loop-video" playsinline></video>
            <button id="mute-toggle" class="mute-button unmuted"></button>
            <div class="swipe-indicator">SWIPE ↕</div>
        \`;
        document.body.appendChild(container);
        
        videoA = document.getElementById('video-a');
        videoB = document.getElementById('video-b');
        
        // Set up mute button
        const muteButton = document.getElementById('mute-toggle');
        muteButton.addEventListener('click', () => {
            const isMuted = videoA.muted;
            videoA.muted = !isMuted;
            videoB.muted = !isMuted;
            muteButton.classList.remove('muted', 'unmuted');
            muteButton.classList.add(!isMuted ? 'muted' : 'unmuted');
        });
        
        // Set up video event listeners
        videoA.addEventListener('ended', () => {
            // Only auto-advance if not currently navigating
            if (!isNavigating && currentVideo === 'A') {
                navigateNext();
            }
        });
        videoB.addEventListener('ended', () => {
            // Only auto-advance if not currently navigating
            if (!isNavigating && currentVideo === 'B') {
                navigateNext();
            }
        });
        
        // Set up navigation
        setupNavigation();
        
        // Load and shuffle video chunks
        initializeVideoQueue();
    }
    
    // Navigation functions
    function navigateNext() {
        if (isNavigating) return;
        
        currentVideoIndex = (currentVideoIndex + 1) % preloadQueue.length;
        if (currentVideoIndex === 0) {
            preloadQueue = shuffle(videoChunks);
        }
        
        const direction = 'up';
        switchVideosWithDirection(currentVideo === 'A' ? 'B' : 'A', direction);
    }
    
    function navigatePrev() {
        if (isNavigating) return;
        
        currentVideoIndex--;
        if (currentVideoIndex < 0) {
            currentVideoIndex = preloadQueue.length - 1;
        }
        
        const direction = 'down';
        switchVideosWithDirection(currentVideo === 'A' ? 'B' : 'A', direction);
    }
    
    // Set up navigation controls
    function setupNavigation() {
        const container = document.getElementById('video-loop-container');
        const swipeIndicator = document.querySelector('.swipe-indicator');
        
        // Scroll wheel navigation for desktop
        let scrollAccumulator = 0;
        let scrollTimeout;
        let lastScrollTime = 0;
        const scrollThreshold = 50; // Minimum scroll distance to trigger navigation
        const scrollDebounceTime = 300; // Minimum time between navigations
        
        container.addEventListener('wheel', (e) => {
            e.preventDefault();
            
            const currentTime = Date.now();
            const timeSinceLastScroll = currentTime - lastScrollTime;
            
            // Clear any existing timeout
            clearTimeout(scrollTimeout);
            
            // Accumulate scroll delta
            scrollAccumulator += e.deltaY;
            
            // Check if accumulated scroll exceeds threshold and enough time has passed
            if (Math.abs(scrollAccumulator) >= scrollThreshold && timeSinceLastScroll > scrollDebounceTime) {
                if (scrollAccumulator > 0) {
                    // Scroll down - next video
                    navigateNext();
                } else {
                    // Scroll up - previous video
                    navigatePrev();
                }
                // Reset accumulator and update last scroll time
                scrollAccumulator = 0;
                lastScrollTime = currentTime;
            }
            
            // Reset accumulator after inactivity
            scrollTimeout = setTimeout(() => {
                scrollAccumulator = 0;
            }, 250);
        }, { passive: false });
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!container.classList.contains('visible')) return;
            
            if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
                e.preventDefault();
                navigatePrev();
            } else if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
                e.preventDefault();
                navigateNext();
            }
        });
        
        // Touch/swipe navigation for mobile
        let touchStartY = 0;
        let touchEndY = 0;
        let touchStartTime = 0;
        let isSwiping = false;
        
        container.addEventListener('touchstart', (e) => {
            // Ignore touches on interactive elements
            if (e.target.closest('.mute-button')) {
                return;
            }
            
            touchStartY = e.touches[0].clientY;
            touchEndY = e.touches[0].clientY; // Reset to start position
            touchStartTime = Date.now();
            isSwiping = false;
            
            // Show swipe indicator on first touch
            if (currentVideoIndex === 0) {
                swipeIndicator.classList.add('visible');
                setTimeout(() => {
                    swipeIndicator.classList.remove('visible');
                }, 3000);
            }
        }, { passive: true });
        
        container.addEventListener('touchmove', (e) => {
            // Ignore touches on interactive elements
            if (e.target.closest('.mute-button')) {
                return;
            }
            
            touchEndY = e.touches[0].clientY;
            const moveDistance = Math.abs(touchStartY - touchEndY);
            
            // Mark as swiping if moved more than 10px
            if (moveDistance > 10) {
                isSwiping = true;
            }
        }, { passive: true });
        
        container.addEventListener('touchend', (e) => {
            // Ignore touches on interactive elements
            if (e.target.closest('.mute-button')) {
                return;
            }
            
            // Only process if it was an actual swipe
            if (!isSwiping) {
                return;
            }
            
            const touchDuration = Date.now() - touchStartTime;
            const swipeDistance = touchStartY - touchEndY;
            const swipeVelocity = Math.abs(swipeDistance) / touchDuration;
            
            // Require minimum swipe distance (80px) and velocity
            if (Math.abs(swipeDistance) > 80 && swipeVelocity > 0.2) {
                if (swipeDistance > 0) {
                    // Swipe up - next video
                    navigateNext();
                } else {
                    // Swipe down - previous video
                    navigatePrev();
                }
            }
        });
    }
    
    // Modified switch function with direction
    function switchVideosWithDirection(nextVideoId, direction) {
        if (isNavigating) return;
        isNavigating = true;
        
        const outgoing = nextVideoId === 'A' ? videoB : videoA;
        const incoming = nextVideoId === 'A' ? videoA : videoB;
        
        // Load the video for the new index
        const videoUrl = \`\${VIDEO_BASE_URL}/\${encodeURIComponent(preloadQueue[currentVideoIndex])}\`;
        incoming.src = videoUrl;
        incoming.load();
        
        // Ensure incoming video is ready
        if (incoming.readyState < 3) {
            incoming.addEventListener('canplay', function playWhenReady() {
                incoming.removeEventListener('canplay', playWhenReady);
                performTransition();
            }, { once: true });
        } else {
            performTransition();
        }
        
        function performTransition() {
            // Apply slide animations
            if (direction === 'up') {
                outgoing.classList.add('slide-up');
                incoming.classList.add('slide-in-up');
            } else {
                outgoing.classList.add('slide-down');
                incoming.classList.add('slide-in-down');
            }
            
            // Start playing incoming video
            incoming.muted = videoA.muted;
            incoming.play().catch(e => {
                console.error('Video play failed:', e);
                // Reset navigation state on error
                isNavigating = false;
                setTimeout(navigateNext, 100);
            });
            
            // Update mute button state to match current mute status
            const muteButton = document.getElementById('mute-toggle');
            if (muteButton) {
                muteButton.classList.remove('muted', 'unmuted');
                muteButton.classList.add(incoming.muted ? 'muted' : 'unmuted');
            }
            
            // Clean up after animation
            setTimeout(() => {
                outgoing.classList.remove('active', 'slide-up', 'slide-down');
                incoming.classList.remove('slide-in-up', 'slide-in-down');
                incoming.classList.add('active');
                
                // Pause the outgoing video to free resources
                outgoing.pause();
                outgoing.currentTime = 0;
                
                currentVideo = nextVideoId;
                
                // Preload next video
                preloadAdjacentVideos();
                
                // Reset navigation lock after transition completes
                // Clear any pending navigation timeouts
                if (navigationTimeout) {
                    clearTimeout(navigationTimeout);
                }
                navigationTimeout = setTimeout(() => {
                    isNavigating = false;
                    navigationTimeout = null;
                }, 100);
            }, 400);
        }
    }
    
    // Preload videos before and after current
    function preloadAdjacentVideos() {
        // Preload next video
        const nextIndex = (currentVideoIndex + 1) % preloadQueue.length;
        const prevIndex = currentVideoIndex === 0 ? preloadQueue.length - 1 : currentVideoIndex - 1;
        
        // Determine which video element is not currently playing
        const inactiveVideo = currentVideo === 'A' ? videoB : videoA;
        
        // Preload next video into inactive element
        const nextUrl = \`\${VIDEO_BASE_URL}/\${encodeURIComponent(preloadQueue[nextIndex])}\`;
        inactiveVideo.src = nextUrl;
        inactiveVideo.load();
    }
    
    // Preload next video in queue
    function preloadNextVideo() {
        const nextVideo = currentVideo === 'A' ? videoB : videoA;
        const videoUrl = \`\${VIDEO_BASE_URL}/\${encodeURIComponent(preloadQueue[currentVideoIndex])}\`;
        
        // Add error handler before setting source
        nextVideo.onerror = function() {
            console.error('Failed to load video:', preloadQueue[currentVideoIndex]);
            // Skip this video and try next one
            currentVideoIndex = (currentVideoIndex + 1) % preloadQueue.length;
            if (currentVideoIndex === 0) {
                preloadQueue = shuffle(videoChunks);
            }
            // Try loading next video
            setTimeout(preloadNextVideo, 100);
        };
        
        nextVideo.src = videoUrl;
        nextVideo.load();
        
        // Move to next video in queue
        currentVideoIndex = (currentVideoIndex + 1) % preloadQueue.length;
        
        // If we've gone through all videos, reshuffle
        if (currentVideoIndex === 0) {
            preloadQueue = shuffle(videoChunks);
        }
    }
    
    // Start the transition - make it globally accessible
    window.startTransition = function() {
        const terminal = document.querySelector('.terminal');
        
        // Create flash overlay
        const flashOverlay = document.createElement('div');
        flashOverlay.className = 'flash-overlay';
        document.body.appendChild(flashOverlay);
        
        // Create video container if not exists
        if (!document.getElementById('video-loop-container')) {
            createVideoContainer();
        }
        
        // Start glitch effect
        if (terminal) {
            terminal.classList.add('glitching');
        }
        
        // Trigger flash after glitch starts
        setTimeout(() => {
            flashOverlay.classList.add('flashing');
            
            // Start video during flash
            setTimeout(() => {
                const container = document.getElementById('video-loop-container');
                container.style.transition = 'none';
                container.style.opacity = '1';
                container.classList.add('visible');
                
                // Start playing first video
                currentVideoIndex = 0;
                videoA.src = \`\${VIDEO_BASE_URL}/\${encodeURIComponent(preloadQueue[currentVideoIndex])}\`;
                // Try to play with audio first
                videoA.play().catch(e => {
                    console.log('Autoplay with audio failed, trying muted:', e);
                    // If audio autoplay fails, mute and try again
                    videoA.muted = true;
                    videoB.muted = true;
                    return videoA.play();
                }).catch(e => console.error('Video play failed:', e));
                
                // Show mute button and update its state
                setTimeout(() => {
                    const muteButton = document.getElementById('mute-toggle');
                    if (muteButton) {
                        muteButton.classList.add('visible');
                        muteButton.classList.remove('muted', 'unmuted');
                        muteButton.classList.add(videoA.muted ? 'muted' : 'unmuted');
                    }
                }, 500);
                
                // Preload adjacent videos
                setTimeout(() => {
                    preloadAdjacentVideos();
                }, 1000);
                
                // Hide terminal
                if (terminal) {
                    terminal.style.display = 'none';
                }
                
                // Clean up flash overlay
                setTimeout(() => {
                    flashOverlay.remove();
                }, 300);
            }, 400); // During peak of flash
        }, 400); // After glitch effect starts
    }
    
    // Start countdown
    function startCountdown() {
        const countdownDiv = document.createElement('div');
        countdownDiv.className = 'line countdown';
        countdownDiv.innerHTML = '> <span style="font-weight: normal;">30</span>';
        
        // Add countdown before email form
        const accessSection = document.querySelector('.access-section');
        const form = document.querySelector('#access-form');
        if (accessSection && form) {
            accessSection.insertBefore(countdownDiv, form);
        }
        
        countdownInterval = setInterval(() => {
            timeRemaining--;
            
            if (timeRemaining <= 0) {
                clearInterval(countdownInterval);
                countdownDiv.style.opacity = '0';
            } else {
                countdownDiv.innerHTML = '> <span style="font-weight: normal;">' + timeRemaining + '</span>';
                
                // Make it flash faster when under 10 seconds
                if (timeRemaining <= 10) {
                    countdownDiv.style.animation = 'blink 0.5s infinite';
                }
                
                // Turn red when under 5 seconds
                if (timeRemaining <= 5) {
                    countdownDiv.style.color = '#ff0000';
                }
            }
        }, 1000);
    }
    
    // Track when countdown starts
    window.countdownStarted = false;
    
    // Initialize on page load
    document.addEventListener('DOMContentLoaded', async function() {
        // Load video chunks first
        videoChunks = await getVideoChunks();
        
        // Simple audio enabler on any interaction
        const enableAudio = () => {
            if (videoA && videoB) {
                // Just try to set unmuted state
                videoA.muted = false;
                videoB.muted = false;
            }
        };
        
        // Listen for any user interaction
        document.addEventListener('click', enableAudio, { once: true });
        document.addEventListener('keydown', enableAudio, { once: true });
        document.addEventListener('touchstart', enableAudio, { once: true });
        
        // Start transition timer only when countdown starts
        window.startVideoTransition = function() {
            if (!window.countdownStarted) {
                window.countdownStarted = true;
                setTimeout(window.startTransition, TRANSITION_DELAY);
            }
        };
        
        // Preload video container but keep it hidden
        createVideoContainer();
        
        // Countdown is now integrated into typing animation
    });
})();
`;

// Complete JavaScript matching Flask glitch.js + video transitions
const TERMINAL_JS = `
// Terminal typing effect and glitch animations
document.addEventListener('DOMContentLoaded', function() {
    // Terminal typing function
    function typeText(element, text, speed = 15) {
        return new Promise((resolve) => {
            let i = 0;
            element.textContent = '';
            element.classList.add('typing-line');
            
            function type() {
                if (i < text.length) {
                    element.textContent += text.charAt(i);
                    i++;
                    setTimeout(type, speed);
                } else {
                    element.classList.remove('typing-line');
                    resolve();
                }
            }
            type();
        });
    }
    
    // Check if we have userData (only on real user pages)
    if (!window.userData) {
        return; // Exit early for access denied pages
    }
    
    // Calculate click latency
    const sentAt = new Date(window.userData.sent_at);
    const clickedAt = new Date();
    const latency = ((clickedAt - sentAt) / 1000).toFixed(1);
    
    // Terminal lines to type
    const lines = [
        { text: '> RECORD_LOOKUP: @' + window.userData.username, class: 'highlight' },
        { text: '> status: ACTIVE', class: 'success' },
        { text: '> profile_id: ' + window.userData.user_id },
        { text: '> follower_count: ' + window.userData.followers },
        { text: '> following_count: ' + window.userData.following },
        { text: '> posts_count: ' + window.userData.posts_count },
        { text: '> engagement_rate: ' + window.userData.engagement_rate },
        { text: '> content_delivered: ' + window.userData.video_sent, class: 'filename' },
        { text: '> delivery_timestamp: ' + window.userData.sent_at },
        { text: '> click_latency: ' + latency + 's' },
        { text: '> selection_criteria: [REDACTED]', class: 'redacted' },
        { text: '> 30', isCountdown: true }
    ];
    
    // Type out each line sequentially
    async function typeAllLines() {
        const container = document.getElementById('data-readout');
        let countdownDiv = null;
        
        for (const lineData of lines) {
            const lineDiv = document.createElement('div');
            lineDiv.className = 'line';
            container.appendChild(lineDiv);
            
            // Check if this is the countdown line
            if (lineData.isCountdown) {
                countdownDiv = lineDiv;
                lineDiv.classList.add('countdown-line');
                await typeText(lineDiv, lineData.text, 10);
                
                // Start countdown after typing
                let timeRemaining = 30;
                
                // Start video transition timer when countdown begins
                if (typeof window.startVideoTransition === 'function') {
                    window.startVideoTransition();
                }
                
                const countdownInterval = setInterval(() => {
                    timeRemaining--;
                    
                    if (timeRemaining <= 0) {
                        clearInterval(countdownInterval);
                        lineDiv.style.opacity = '0.3';
                        lineDiv.innerHTML = '> <span style="opacity: 0.5;">[EXPIRED]</span>';
                    } else {
                        lineDiv.innerHTML = '> <span class="countdown-text">' + 
                            timeRemaining.toString().padStart(2, '0') + 
                            '</span>';
                        
                        // Subtle opacity changes as time decreases
                        if (timeRemaining <= 10) {
                            lineDiv.style.opacity = '0.7';
                        }
                    }
                }, 1000);
            } else if (lineData.class) {
                const parts = lineData.text.split(': ');
                if (parts.length > 1) {
                    await typeText(lineDiv, parts[0] + ': ', 10);
                    const span = document.createElement('span');
                    span.className = lineData.class;
                    lineDiv.appendChild(span);
                    await typeText(span, parts[1], 15);
                } else {
                    await typeText(lineDiv, lineData.text, 10);
                }
            } else {
                await typeText(lineDiv, lineData.text, 10);
            }
            
            // Pause between lines
            await new Promise(resolve => setTimeout(resolve, 50));
        }
        
        // Show access section immediately after data is typed
        setTimeout(() => {
            document.querySelector('.access-section').style.opacity = '1';
        }, 300);
    }
    
    // Start typing animation
    typeAllLines();
    
    // Handle email input
    const emailInput = document.getElementById('email-input');
    const cursor = document.getElementById('cursor');
    
    // Function to measure text width
    function getTextWidth(text, font) {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        context.font = font;
        return context.measureText(text).width;
    }
    
    // Move cursor to end of text
    function updateCursorPosition() {
        const inputStyle = window.getComputedStyle(emailInput);
        const font = inputStyle.fontSize + ' ' + inputStyle.fontFamily;
        const textWidth = getTextWidth(emailInput.value, font);
        cursor.style.left = textWidth + 'px';
    }
    
    // Update cursor position when input changes
    emailInput.addEventListener('input', updateCursorPosition);
    emailInput.addEventListener('keyup', updateCursorPosition);
    emailInput.addEventListener('paste', () => setTimeout(updateCursorPosition, 0));
    
    // Keep input always focused
    emailInput.addEventListener('blur', () => {
        setTimeout(() => emailInput.focus(), 0);
    });
    
    // Focus input when user clicks anywhere on the page
    document.addEventListener('click', (e) => {
        if (e.target !== emailInput) {
            emailInput.focus();
        }
    });
    
    // Enable typing anywhere on the page
    document.addEventListener('keydown', (e) => {
        if (document.activeElement !== emailInput && !e.ctrlKey && !e.metaKey && !e.altKey) {
            emailInput.focus();
        }
    });
    
    // Set initial cursor position
    updateCursorPosition();
    
    // Handle form submission
    const form = document.getElementById('access-form');
    const responseDiv = document.getElementById('response-message');
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = document.getElementById('email-input').value;
        
        try {
            const response = await fetch('/api/email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email, username: window.userData.username }),
                credentials: 'same-origin'
            });
            
            const data = await response.json();
            
            responseDiv.textContent = '> ACCESS GRANTED';
            responseDiv.className = 'success';
            
            form.style.display = 'none';
            setTimeout(() => {
                responseDiv.textContent += '\\n> AWAIT PHASE_2 ACTIVATION';
            }, 1000);
            
            // Add glitch effect
            setTimeout(() => {
                document.body.classList.add('glitch');
                setTimeout(() => {
                    document.body.classList.remove('glitch');
                }, 500);
            }, 2000);
        } catch (error) {
            responseDiv.textContent = '> SYSTEM ERROR';
            responseDiv.className = 'error';
        }
    });
    
    // Random glitch on certain elements
    const glitchElements = document.querySelectorAll('.redacted, .highlight');
    setInterval(() => {
        const element = glitchElements[Math.floor(Math.random() * glitchElements.length)];
        if (element) {
            element.style.transform = 'translateX(' + (Math.random() * 4 - 2) + 'px)';
            setTimeout(() => {
                element.style.transform = 'translateX(0)';
            }, 100);
        }
    }, 5000);
    
    // Console easter egg
    console.log(SHARED_ASSETS.ASCII_ART + '\n\n' + SHARED_ASSETS.TAGLINE);
});
`;

// Build mystery HTML using shared templates
function buildMysteryHTML(username, userData) {
  const terminalContent = `
    <div class="header">
        ${SHARED_ASSETS.VHS_GHOST_SPAN}
    </div>
    
    <div class="data-readout">
        <div class="terminal-line">
            <span class="typing">SYSTEM: <span id="system-status">ANALYZING...</span></span>
        </div>
        <div class="terminal-line">
            <span class="typing">PROFILE: <span class="data-value" id="profile-username">@${username}</span></span>
        </div>
        <div class="terminal-line">
            <span class="typing">FOLLOWERS: <span class="data-value" id="followers-count">████████</span></span>
        </div>
        <div class="terminal-line">
            <span class="typing">ENGAGEMENT: <span class="data-value" id="engagement-rate">██.██%</span></span>
        </div>
        <div class="terminal-line">
            <span class="typing">POSTS: <span class="data-value" id="posts-count">███</span></span>
        </div>
        <div class="terminal-line">
            <span class="typing">FOLLOWING: <span class="data-value" id="following-count">████</span></span>
        </div>
        <div class="terminal-line">
            <span class="typing">AVG_LIKES: <span class="data-value" id="avg-likes">█,███</span></span>
        </div>
        <div class="terminal-line">
            <span class="typing">DELIVERED: <span class="data-value" id="delivery-time">█████</span></span>
        </div>
        <div class="terminal-line countdown">
            <span id="countdown-line"></span>
        </div>
    </div>
    
    <div id="email-section" class="hidden">
        <div class="prompt">
            <span>> ENTER_EMAIL_FOR_ACCESS: </span>
            <div class="input-wrapper">
                <input 
                    type="email" 
                    id="email-input" 
                    class="terminal-input" 
                    placeholder="ghost@vhs.com"
                    autocomplete="off"
                    spellcheck="false"
                    maxlength="100"
                    style="min-width: 250px;"
                >
                <span class="block-cursor"></span>
            </div>
        </div>
        <div id="response-message" class="hidden"></div>
    </div>
  `;
  
  return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SYSTEM_DIAGNOSTIC</title>
    <style>${TERMINAL_CSS}</style>
</head>
<body>
    ${createTerminalHTML(terminalContent)}
    
    <script>
    // Embed user data
    const userData = ${JSON.stringify(userData)};
    </script>
    <script>${TERMINAL_JS}</script>
    <script>${VIDEO_TRANSITION_JS}</script>
</body>
</html>`;
}


// Additional styles for access denied page
const ACCESS_DENIED_STYLES = `
.warning {
    color: #ffff00;
}

/* Hide lines initially for animation */
.data-readout .line {
    opacity: 0;
}

.streaming-logs {
    margin: 30px 0;
    padding: 20px 0;
    border-top: 1px solid #00ff00;
    border-bottom: 1px solid #00ff00;
    opacity: 0;
    transition: opacity 0.5s ease-in;
}

.log-line {
    opacity: 0.6;
    font-size: 12px;
    margin: 5px 0;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
`;

// Access denied JS with video transitions
const ACCESS_DENIED_JS = `
// Reuse the countdown timer function
${createCountdownTimer.toString()}

// Add typing effect to lines and countdown
document.addEventListener('DOMContentLoaded', function() {
    const lines = document.querySelectorAll('.line');
    
    lines.forEach((line, index) => {
        setTimeout(() => {
            line.style.animation = 'fadeIn 0.3s forwards';
            
            // Check if this is the countdown line
            if (line.classList.contains('countdown-line')) {
                // Start countdown after line appears
                setTimeout(() => {
                    createCountdownTimer(line, 10, {
                        prefix: '> ',
                        suffix: '',
                        onComplete: () => {
                            // Trigger video transition
                            if (typeof window.startTransition === 'function') {
                                window.startTransition();
                            } else if (typeof startTransition === 'function') {
                                startTransition();
                            } else {
                                line.style.opacity = '0.3';
                                line.innerHTML = '<span>> [EXPIRED]</span>';
                            }
                        },
                        blinkAt: -1, // No blinking for access denied
                        normalStyle: 'font-weight: normal;'
                    });
                }, 300); // Start countdown shortly after line appears
            }
        }, index * 100);
    });
});
`;

// Build access denied HTML using shared templates
function buildAccessDeniedHTML(options = {}) {
  const { message = 'ACCESS DENIED', timestamp = new Date().toISOString(), username = 'unknown' } = options;
  
  const terminalContent = `
    <div class="header">
        ${SHARED_ASSETS.VHS_GHOST_SPAN}
    </div>
    
    <div class="data-readout">
        <div class="line">
            <span class="warning">&gt; ▓▓▓ INVALID AUTHENTICATION ▓▓▓</span>
        </div>
        <div class="line">&nbsp;</div>
        <div class="line">
            <span>&gt; TIMESTAMP:</span> <span class="highlight">${timestamp}</span>
        </div>
        <div class="line">
            <span>&gt; ATTEMPTED SUBJECT:</span> <span class="redacted">@${username}</span>
        </div>
        <div class="line">
            <span>&gt; AUTHENTICATION:</span> <span class="warning">FAILED</span>
        </div>
        <div class="line countdown-line">
            <span>&gt; 10</span>
        </div>
        <div class="line">&nbsp;</div>
        <div class="line">
            <span class="warning">&gt; ${message}</span>
        </div>
        <div class="line">&nbsp;</div>
        <div class="line">
            <span class="glitch" data-text="&gt; THE SIGNAL IS NOT FOR YOU">&gt; THE SIGNAL IS NOT FOR YOU</span>
        </div>
    </div>
  `;
  
  return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ACCESS_DENIED</title>
    <style>${TERMINAL_CSS}${ACCESS_DENIED_STYLES}</style>
</head>
<body>
    ${createTerminalHTML(terminalContent)}
    
    <script>${ACCESS_DENIED_JS}</script>
    <script>${VIDEO_TRANSITION_JS}</script>
</body>
</html>`;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname.slice(1); // Remove leading slash
    const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
    
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      const origin = request.headers.get('Origin');
      const allowedOrigins = ['https://vhs-ghost.com', 'http://localhost:5000', 'http://localhost:8787'];
      const corsOrigin = allowedOrigins.includes(origin) ? origin : 'https://vhs-ghost.com';
      
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': corsOrigin,
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
          'Access-Control-Allow-Credentials': 'true',
        },
      });
    }
    
    // Handle root path
    if (!path) {
      const timestamp = new Date().toISOString();
      const ip = request.headers.get('CF-Connecting-IP') || '127.0.0.1';
      return new Response(
        buildAccessDeniedHTML({ 
          message: 'ACCESS DENIED', 
          timestamp, 
          username: escapeHtml('unknown') 
        }),
        {
          status: 404,
          headers: { 'Content-Type': 'text/html' },
        }
      );
    }
    
    // Handle email list endpoint (diagnostic)
    if (path === 'api/emails' && request.method === 'GET') {
      try {
        // Check for API secret
        const url = new URL(request.url);
        const providedSecret = url.searchParams.get('secret');
        
        // Verify secret matches environment variable
        if (!env.EMAILS_API_SECRET || providedSecret !== env.EMAILS_API_SECRET) {
          return new Response(JSON.stringify({ error: 'Unauthorized' }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' }
          });
        }
        
        if (!env.EMAILS_KV) {
          return new Response(JSON.stringify({ error: 'KV not available' }), {
            status: 500,
            headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
          });
        }
        
        const list = await env.EMAILS_KV.list();
        const emails = [];
        
        // Get values for each key
        for (const key of list.keys) {
          const value = await env.EMAILS_KV.get(key.name);
          emails.push({
            key: key.name,
            data: value ? JSON.parse(value) : null
          });
        }
        
        return new Response(JSON.stringify({ 
          count: emails.length,
          emails: emails,
          debug: 'Listed from KV'
        }), {
          headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
        });
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), {
          status: 500,
          headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
        });
      }
    }
    
    // Handle email API endpoint
    if (path === 'api/email' && request.method === 'POST') {
      try {
        // Basic rate limiting - check IP
        const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
        const rateLimitKey = `ratelimit_email_${ip}`;
        
        // Check rate limit (5 submissions per hour per IP)
        if (env.EMAILS_KV) {
          const recentSubmissions = await env.EMAILS_KV.get(rateLimitKey);
          if (recentSubmissions) {
            const submissions = JSON.parse(recentSubmissions);
            const hourAgo = Date.now() - (60 * 60 * 1000);
            const recentCount = submissions.filter(ts => ts > hourAgo).length;
            
            if (recentCount >= 5) {
              return new Response(
                JSON.stringify({ success: false, message: 'RATE LIMIT EXCEEDED' }),
                {
                  status: 429,
                  headers: { 
                    'Content-Type': 'application/json',
                    'X-RateLimit-Limit': '5',
                    'X-RateLimit-Remaining': '0'
                  },
                }
              );
            }
          }
        }
        
        const { email, username } = await request.json();
        
        // Basic validation - check it's not empty and has @ symbol
        if (!email || email.trim().length === 0 || !email.includes('@')) {
          throw new Error('Invalid input');
        }
        
        // Truncate to 200 chars for safety
        const sanitizedEmail = email.substring(0, 200);
        
        // In production, save to Workers KV
        if (env.EMAILS_KV) {
          const emailKey = `email_${sanitizedEmail.replace(/[^a-zA-Z0-9@._-]/g, '_')}_${Date.now()}`;
          try {
            await env.EMAILS_KV.put(emailKey, JSON.stringify({
              email: sanitizedEmail,
              username,
              timestamp: new Date().toISOString(),
              ip: ip
            }));
            
            // Update rate limit counter
            const currentSubmissions = await env.EMAILS_KV.get(rateLimitKey);
            const submissions = currentSubmissions ? JSON.parse(currentSubmissions) : [];
            submissions.push(Date.now());
            await env.EMAILS_KV.put(rateLimitKey, JSON.stringify(submissions), {
              expirationTtl: 3600 // Expire after 1 hour
            });
          } catch (kvError) {
            console.error('KV Write Error:', kvError.message);
            throw kvError;
          }
        }
        
        return new Response(
          JSON.stringify({ 
            success: true, 
            message: 'ACCESS GRANTED'
          }),
          {
            headers: { 
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': 'https://vhs-ghost.com'
            },
          }
        );
      } catch (e) {
        return new Response(
          JSON.stringify({ success: false, message: 'SYSTEM ERROR' }),
          {
            status: 400,
            headers: { 
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': 'https://vhs-ghost.com'
            },
          }
        );
      }
    }
    
    // Handle chunks API endpoint - returns chunks from R2 bucket dynamically
    if (path === 'api/chunks' && request.method === 'GET') {
      try {
        let chunks = [];
        
        // Get chunks from R2 bucket
        if (env.CHUNKS_BUCKET) {
          const list = await env.CHUNKS_BUCKET.list({ limit: 1000 });
          
          // Filter for .mp4 files and randomize
          const allChunks = list.objects
            .filter(obj => obj.key.endsWith('.mp4'))
            .map(obj => obj.key);
          
          // Shuffle all chunks for random variety
          for (let i = allChunks.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [allChunks[i], allChunks[j]] = [allChunks[j], allChunks[i]];
          }
          
          chunks = allChunks; // Return all videos, no limit
        }
        
        // Return empty array if no chunks found
        return new Response(
          JSON.stringify({ chunks: chunks || [] }),
          {
            headers: { 
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': '*',
              'Cache-Control': 'max-age=300' // Cache for 5 minutes
            },
          }
        );
      } catch (error) {
        console.error('Error fetching chunks:', error);
        return new Response(
          JSON.stringify({ chunks: [] }),
          {
            headers: { 
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': '*'
            },
          }
        );
      }
    }
    
    // Handle video serving endpoint - serve videos from R2 bucket through Worker
    if (path.startsWith('api/video/') && request.method === 'GET') {
      try {
        // Check referrer to prevent hotlinking
        const referrer = request.headers.get('Referer') || request.headers.get('Referrer') || '';
        const origin = request.headers.get('Origin') || '';
        
        // Allow if referrer is from our domain or common local dev environments
        const allowedReferrers = [
          'https://vhs-ghost.com',
          'https://vhs-ghost.takeatripbags.workers.dev',
          'http://localhost',
          'http://127.0.0.1'
        ];
        
        const isAllowedReferrer = allowedReferrers.some(allowed => 
          referrer.startsWith(allowed) || origin.startsWith(allowed)
        );
        
        // Also allow if no referrer (direct access, some privacy tools strip referrer)
        // This is important for mobile apps and privacy-focused browsers
        const isDirectAccess = !referrer && !origin;
        
        if (!isAllowedReferrer && !isDirectAccess) {
          console.log('Video access blocked - Invalid referrer:', referrer, 'Origin:', origin);
          return new Response('Access denied', { 
            status: 403,
            headers: {
              'Content-Type': 'text/plain',
              'Cache-Control': 'no-cache'
            }
          });
        }
        
        let videoName = path.replace('api/video/', '');
        
        // Decode the URL-encoded filename
        videoName = decodeURIComponent(videoName);
        
        console.log('Requested video:', videoName);
        
        if (!env.CHUNKS_BUCKET) {
          return new Response('Video service unavailable', { status: 503 });
        }
        
        // Try to get the object with the decoded name
        let object = await env.CHUNKS_BUCKET.get(videoName);
        
        // If not found and it's missing the .mp4 extension, try adding it
        if (!object && !videoName.endsWith('.mp4')) {
          object = await env.CHUNKS_BUCKET.get(videoName + '.mp4');
        }
        
        // If not found, try some common variations
        if (!object) {
          // Try with spaces replaced by underscores
          const underscoreName = videoName.replace(/ /g, '_');
          object = await env.CHUNKS_BUCKET.get(underscoreName);
        }
        
        if (!object) {
          console.error('Video not found in R2:', videoName);
          // List first few files to debug
          const list = await env.CHUNKS_BUCKET.list({ limit: 5 });
          console.log('Sample files in bucket:', list.objects.map(o => o.key));
          return new Response(`Video not found: ${videoName}`, { status: 404 });
        }
        
        const headers = new Headers();
        object.writeHttpMetadata(headers);
        headers.set('Accept-Ranges', 'bytes');
        headers.set('Access-Control-Allow-Origin', '*');
        headers.set('Content-Type', 'video/mp4');
        headers.set('Cache-Control', 'public, max-age=3600');
        
        return new Response(object.body, { headers });
      } catch (error) {
        console.error('Error serving video:', error);
        return new Response('Error loading video: ' + error.message, { status: 500 });
      }
    }
    
    // Look up user - first try KV, then fallback to static data
    let userData = null;
    
    // Sanitize the username from the path to prevent XSS
    const rawUsername = path;
    const sanitizedUsername = sanitizeUsername(rawUsername);
    
    // Try KV first if available
    if (env.USERS_KV) {
      const kvData = await env.USERS_KV.get(sanitizedUsername);
      if (kvData) {
        userData = JSON.parse(kvData);
      }
    }
    
    // Fallback to static test data
    if (!userData) {
      userData = getUserData(sanitizedUsername);
    }
    
    if (!userData) {
      const timestamp = new Date().toISOString();
      const ip = request.headers.get('CF-Connecting-IP') || '127.0.0.1';
      return new Response(
        buildAccessDeniedHTML({ 
          message: 'STATUS: NO MATCH IN DATABASE', 
          timestamp, 
          username: escapeHtml(sanitizedUsername) 
        }),
        {
          status: 404,
          headers: { 'Content-Type': 'text/html' },
        }
      );
    }
    
    // Format numbers with commas
    function formatNumber(num) {
      return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
    
    // Prepare user data for JavaScript
    const jsUserData = {
      username: userData.username,
      user_id: userData.user_id,
      followers: formatNumber(userData.followers),
      following: formatNumber(userData.following),
      posts_count: userData.posts_count.toString(),
      engagement_rate: (userData.avg_engagement * 100).toFixed(2) + '%',
      video_sent: userData.video_sent.replace('.mp4', '').toUpperCase(),
      sent_at: userData.sent_at
    };
    
    // Render the page with user data
    const html = buildMysteryHTML(userData.username, jsUserData);
    
    return new Response(html, {
      headers: { 
        'Content-Type': 'text/html',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer'
      },
    });
  },
};