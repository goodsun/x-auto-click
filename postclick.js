// postclick.js - XのツイートボタンをWaitしてクリック
function waitAndClick(maxMs = 15000) {
  const start = Date.now();
  const timer = setInterval(() => {
    const btn = document.querySelector('[data-testid="tweetButton"]');
    if (btn && !btn.disabled) {
      btn.click();
      clearInterval(timer);
    } else if (Date.now() - start > maxMs) {
      clearInterval(timer);
      console.error('[postclick] tweetButton not found within timeout');
    }
  }, 500);
}
waitAndClick();
