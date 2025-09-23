// SPDX-License-Identifier: MIT
// Copyright (c) 2025 Xinchen Wang 王欣辰

const puppeteer = require('/opt/node_app/node_modules/puppeteer');
async function searchLinks(searchQuery) {
  if (!searchQuery) {
    throw new Error('Please provide the searching keywords!');
  }

  const browser = await puppeteer.launch({ headless: true , args: ['--no-sandbox', '--disable-setuid-sandbox']});
  const page = await browser.newPage();
  
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36');
  
  await page.setExtraHTTPHeaders({
    'Accept-Language': 'en-US,en;q=0.9'
  });

  await page.goto('https://www.bing.com');
  await page.type('input[name="q"]', searchQuery);
  await page.keyboard.press('Enter');

  await page.waitForSelector('li.b_algo h2 a', { timeout: 10000 });

  const links = await page.evaluate(() => {
    const anchors = document.querySelectorAll('li.b_algo h2 a');
    return Array.from(anchors).map(anchor => anchor.href);
  });

  await browser.close();
  return links;
}

const searchQuery = process.argv[2];

searchLinks(searchQuery)
  .then(links => {
    console.log(JSON.stringify(links));
  })
  .catch(error => {
    console.error('Error:', error);
  });