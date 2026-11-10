#!/usr/bin/env node
const { chromium } = require('playwright');
const fs = require('fs');

const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));

async function pickOption(page, text) {
  // waitForSelector times out when hidden select__menu elements exist on page;
  // wait for a visible option element matching the target text instead
  const optByClass = page.locator('[class*="select__option"]').filter({ hasText: text }).first();
  await optByClass.waitFor({ state: 'visible', timeout: 10000 });
  const optByRole = page.getByRole('option', { name: text, exact: true }).first();
  if (await optByRole.count() > 0) { await optByRole.click(); }
  else { await optByClass.click(); }
  await page.waitForTimeout(300);
}

async function openDropdown(page, fieldId) {
  // Dismiss any open dropdown before opening another
  await page.keyboard.press('Escape');
  await page.waitForTimeout(200);

  // React Select pattern: .select__control:has(#react-select-{id}-placeholder)
  const rsCtrl = page.locator(`.select__control:has(#react-select-${fieldId}-placeholder)`);
  if (await rsCtrl.count() > 0) {
    await rsCtrl.scrollIntoViewIfNeeded();
    await page.waitForTimeout(200);
    await rsCtrl.click();
    await page.waitForTimeout(500);
    return;
  }
  // Greenhouse button flyout pattern
  const field = page.locator(`#${fieldId}`);
  const parent = field.locator('xpath=ancestor::div[@class][1]');
  const toggle = parent.locator('button[type="button"]').last();
  await toggle.click({ timeout: 5000 });
  await page.waitForTimeout(300);
}

async function fillByLabel(page, labelTextPart, value, type) {
  const label = page.locator('label').filter({ hasText: new RegExp(labelTextPart, 'i') }).first();
  // Fail fast if label not found — avoids 30s timeouts on missing EEO sections
  if (await label.count() === 0) throw new Error(`label not found: ${labelTextPart}`);
  const forAttr = await label.getAttribute('for').catch(() => null);
  if (type === 'dropdown') {
    if (forAttr) { await openDropdown(page, forAttr); }
    else { await label.locator('xpath=following::button[@type="button"][1]').click({ timeout: 5000 }); }
    await pickOption(page, value);
  } else {
    if (forAttr) { await page.locator(`#${forAttr}`).fill(value); }
    else { await page.locator(`[aria-label*="${labelTextPart}"]`).first().fill(value); }
  }
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  const url = `https://job-boards.greenhouse.io/embed/job_app?for=${cfg.for}&token=${cfg.token}`;
  console.error('Navigating:', url);
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });

  const a = cfg.applicant;
  await page.locator('#first_name').fill(a.first_name);
  await page.locator('#last_name').fill(a.last_name);
  await page.locator('#email').fill(a.email);
  await page.locator('#phone').fill(a.phone);

  // Country combobox
  await page.locator('#country').click();
  await page.waitForTimeout(400);
  await page.locator('#country').fill('United');
  await page.waitForTimeout(500);
  await page.getByRole('option', { name: /United States/, exact: false }).first().click();
  await page.waitForTimeout(300);

  // Location — optional
  const locationInput = page.locator('#candidate-location');
  if (await locationInput.count() > 0 && a.city) {
    const cityShort = a.city.split(',')[0].trim();
    await locationInput.fill(cityShort);
    await page.waitForTimeout(1500);
    const stateAbbr = a.city.split(',')[1]?.trim() || '';
    const opts = page.getByRole('option');
    const count = await opts.count();
    let picked = false;
    for (let i = 0; i < count; i++) {
      const t = await opts.nth(i).textContent();
      if (stateAbbr && t && t.includes(stateAbbr.split(' ')[0])) { await opts.nth(i).click(); picked = true; break; }
    }
    if (!picked && count > 0) await opts.first().click();
    await page.waitForTimeout(300);
  }

  // Resume upload
  await page.locator('input[type="file"]').first().setInputFiles(cfg.resume_path);
  await page.waitForTimeout(1000);

  // Custom questions
  for (const q of (cfg.questions || [])) {
    console.error('Filling:', q.label.slice(0, 60));
    try { await fillByLabel(page, q.label, q.value, q.type || 'text'); }
    catch (e) { console.error('  WARN:', e.message.slice(0, 100)); }
    await page.waitForTimeout(200);
  }

  // EEO (graceful — skip fields that don't exist on this form)
  const eeo = cfg.eeo || {};
  for (const [part, val, type] of [
    ['Gender', eeo.gender, 'dropdown'],
    ['Hispanic', eeo.hispanic != null ? (eeo.hispanic ? 'Yes' : 'No') : null, 'dropdown'],
    ['identify your race', eeo.race, 'dropdown'],
    ['Veteran', eeo.veteran, 'dropdown'],
  ]) {
    if (!val) continue;
    try { await fillByLabel(page, part, val, type); }
    catch (e) { console.error(`  WARN EEO ${part}:`, e.message.slice(0, 80)); }
  }

  if (cfg.screenshot_before_submit) {
    await page.screenshot({ path: cfg.screenshot_before_submit, fullPage: true });
    console.error('Screenshot:', cfg.screenshot_before_submit);
  }

  await page.locator('button[type="submit"]').click();
  await page.waitForTimeout(5000);

  const finalUrl = page.url();
  const title = await page.title();
  const bodyText = await page.locator('body').textContent().catch(() => '');
  const confirmed = /thank|confirm|submitted|success/i.test(bodyText + title);

  console.log(JSON.stringify({ success: confirmed, url: finalUrl, title, body_preview: bodyText.slice(0, 200).trim() }));
  await browser.close();
})().catch(err => {
  console.error('Fatal:', err.message);
  console.log(JSON.stringify({ success: false, error: err.message }));
  process.exit(1);
});
