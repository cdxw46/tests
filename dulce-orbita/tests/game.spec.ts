import { expect, test } from '@playwright/test'

test('renders a complete playable board and starts a spin', async ({ page }) => {
  await page.goto('/')

  await expect(page).toHaveTitle(/Dulce Órbita/)
  await expect(page.getByRole('grid')).toBeVisible()
  await expect(page.getByRole('gridcell')).toHaveCount(49)

  const spin = page.getByRole('button', { name: 'Girar' })
  await expect(spin).toBeEnabled()
  await spin.click()
  await expect(page.getByRole('button', { name: 'Cascada en curso' })).toBeDisabled()
  await expect(page.getByText(/LANZANDO|COMBINACIÓN|CASCADA|PREMIO|CASI/).first()).toBeVisible()
})

test('keeps mobile controls within the viewport and opens game info', async ({
  page,
}, testInfo) => {
  test.skip(!testInfo.project.name.includes('mobile'), 'Mobile layout check')
  await page.goto('/')

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  )
  expect(overflow).toBeLessThanOrEqual(1)

  await page.getByRole('button', { name: /INFO/ }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Agrupa, explota, repite' })).toBeVisible()
})
