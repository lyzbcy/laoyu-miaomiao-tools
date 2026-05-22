const fs = require('fs');
const path = require('path');

// Read the comments data
const commentsData = JSON.parse(fs.readFileSync('./runtime/input/comments_for_reply.json', 'utf8'));

// Read the template configuration
const templates = JSON.parse(fs.readFileSync('./templates/default.json', 'utf8'));

// Generate replies
const replies = commentsData.comments.map(comment => {
  const { username, commentText, intent, priority } = comment;
  
  let replyText;
  
  // Check if user is special user (🎀星星布丁🎀)
  if (templates.specialUsers[username]) {
    const specialUser = templates.specialUsers[username];
    const examples = specialUser.examples;
    replyText = examples[Math.floor(Math.random() * examples.length)];
  } else {
    // Check for malicious content
    const isMalicious = templates.maliciousDetection.keywords.some(keyword => 
      commentText.toLowerCase().includes(keyword.toLowerCase())
    );
    
    if (isMalicious) {
      const maliciousTemplates = templates.maliciousReplyTemplates;
      replyText = maliciousTemplates[Math.floor(Math.random() * maliciousTemplates.length)];
    } else {
      // Use professional voice templates
      const voiceTemplates = templates.voices.professional;
      if (voiceTemplates[intent] && voiceTemplates[intent].public) {
        replyText = voiceTemplates[intent].public;
      } else {
        // Default fallback for unknown intents
        replyText = "感谢关注！这个我会继续分享~";
      }
    }
  }
  
  return {
    username,
    commentText,
    replyText: `${templates.prefix}${replyText}${templates.suffix}`,
    intent,
    priority,
    workTitle: commentsData.selectedWork.title
  };
});

// Output the generated replies
const output = {
  ...commentsData,
  generatedReplies: replies,
  generatedAt: new Date().toISOString(),
  totalReplies: replies.length
};

fs.writeFileSync('./runtime/output/generated_replies.json', JSON.stringify(output, null, 2));
console.log(`Generated ${replies.length} replies for work: ${commentsData.selectedWork.title}`);
replies.forEach(reply => {
  console.log(`${reply.username}: ${reply.replyText}`);
});