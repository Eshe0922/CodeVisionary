// SPDX-License-Identifier: MIT
// Copyright (c) 2025 Xinchen Wang 王欣辰

const puppeteer = require('/opt/node_app/node_modules/puppeteer');
const fs = require('fs');
const path = require('path');

(async () => {

  const filePath = process.argv[2];
  const outputFileName = process.argv[3];
  const actions = process.argv.slice(4); 
  console.log(actions);
  if (!filePath || !outputFileName) {
    console.error('Please provide the file path and output image file name as parameters!');
    process.exit(1);
  }

  const browser = await puppeteer.launch({
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();

  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.error('PAGE ERROR:', msg.text());
    }
  });

  const htmlContent = fs.readFileSync(filePath, 'utf8');
  await page.setContent(htmlContent);

  for (const action of actions) {
    const [command, selector, ...args] = action.split(':');
    const elementExists = await page.$(selector) !== null;
    if (!elementExists) {
      console.error(`Element not found: ${selector}`);
      continue;
    }

    switch (command) {
      case 'click':
        await page.click(selector);
        console.log('Clicked:', selector);
        break;
      case 'fill':
        const text = args.join(':');
        await page.type(selector, text);
        console.log('Filled:', text, 'into', selector);
        break;
      case 'hover':
        await page.hover(selector);
        console.log('Hovered over:', selector);
        break;
      case 'scroll':
        const [scrollLeft, scrollTop] = args.map(Number);
        await page.evaluate((selector, scrollLeft, scrollTop) => {
          const element = document.querySelector(selector);
          if (element) {
            element.scrollLeft = scrollLeft || 0;
            element.scrollTop = scrollTop || 0;
          }
        }, selector, scrollLeft, scrollTop);
        console.log('Scrolled', scrollLeft, 'px horizontally and', scrollTop, 'px vertically in', selector);
        break;
      default:
        console.error(`Unknown command: ${command}`);
    }
  }

  await new Promise(resolve => setTimeout(resolve, 3000));

  await page.screenshot({ path: outputFileName, fullPage: true });

  await browser.close();
})();