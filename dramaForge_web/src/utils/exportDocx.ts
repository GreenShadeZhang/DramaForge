import { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType } from 'docx'
import type { ScriptDetail } from '@/types/script'

/**
 * Export script to .docx and trigger download
 */
export async function exportScriptToDocx(
  script: ScriptDetail,
  projectTitle?: string,
) {
  const children: Paragraph[] = []

  // ── Title ──
  if (projectTitle) {
    children.push(
      new Paragraph({
        text: `《${projectTitle}》`,
        heading: HeadingLevel.TITLE,
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
      }),
    )
  }

  children.push(
    new Paragraph({
      text: '剧本',
      heading: HeadingLevel.HEADING_1,
      alignment: AlignmentType.CENTER,
      spacing: { after: 400 },
    }),
  )

  // ── 剧本摘要 ──
  const metaItems: { label: string; value?: string }[] = [
    { label: '主角', value: script.protagonist },
    { label: '类型', value: script.genre },
    { label: '一句话故事', value: script.one_liner },
    { label: '梗概', value: script.synopsis },
    { label: '背景设定', value: script.background },
    { label: '场景设定', value: script.setting },
  ]

  const hasMeta = metaItems.some((i) => i.value)
  if (hasMeta) {
    children.push(
      new Paragraph({
        text: '剧本摘要',
        heading: HeadingLevel.HEADING_1,
        spacing: { before: 400, after: 200 },
      }),
    )
    metaItems.forEach((item) => {
      if (item.value) {
        children.push(
          new Paragraph({
            children: [
              new TextRun({ text: `${item.label}：`, bold: true, size: 24 }),
              new TextRun({ text: item.value, size: 24 }),
            ],
            spacing: { after: 120 },
          }),
        )
      }
    })
  }

  // ── 分集剧本 ──
  if (script.episodes && script.episodes.length > 0) {
    children.push(
      new Paragraph({
        text: '分集剧本',
        heading: HeadingLevel.HEADING_1,
        spacing: { before: 400, after: 200 },
      }),
    )

    script.episodes.forEach((ep) => {
      children.push(
        new Paragraph({
          text: `第${ep.number}集  ${ep.title || ''}`,
          heading: HeadingLevel.HEADING_2,
          spacing: { before: 300, after: 120 },
        }),
      )

      if (ep.content) {
        // Split content into paragraphs and add each as a paragraph
        const lines = ep.content.split('\n')
        lines.forEach((line) => {
          const trimmed = line.trim()
          if (!trimmed) {
            children.push(new Paragraph({ spacing: { after: 120 } }))
            return
          }
          children.push(
            new Paragraph({
              children: [new TextRun({ text: trimmed, size: 22 })],
              spacing: { after: 80 },
              indent: { firstLine: 440 }, // 2-char indent for Chinese
            }),
          )
        })
      }
    })
  }

  const doc = new Document({
    styles: {
      default: {
        document: {
          run: {
            font: 'SimSun',
            size: 22, // ~11pt
          },
        },
      },
    },
    sections: [{ children }],
  })

  const blob = await Packer.toBlob(doc)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${projectTitle || '剧本'}.docx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
