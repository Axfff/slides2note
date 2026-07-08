import katex from "katex";
import "katex/dist/katex.min.css";

type Delimiter = {
  start: string;
  end: string;
  display: boolean;
};

type Segment =
  | {
      type: "text";
      value: string;
    }
  | {
      type: "math";
      value: string;
      display: boolean;
    };

type Props = {
  text: string;
  as?: "p" | "span" | "div" | "blockquote" | "pre";
  className?: string;
};

const DELIMITERS: Delimiter[] = [
  { start: "$$", end: "$$", display: true },
  { start: "\\[", end: "\\]", display: true },
  { start: "\\(", end: "\\)", display: false },
  { start: "$", end: "$", display: false },
];

export function MathText({ text, as: Tag = "span", className }: Props) {
  const children = parseMathSegments(text).map((segment, index) => {
    if (segment.type === "text") {
      return <span key={index}>{segment.value}</span>;
    }

    const html = katex.renderToString(segment.value, {
      displayMode: segment.display,
      throwOnError: false,
      strict: "ignore",
      trust: false,
      output: "html",
    });

    return (
      <span
        className={segment.display ? "math-text math-text--display" : "math-text"}
        dangerouslySetInnerHTML={{ __html: html }}
        key={index}
      />
    );
  });

  return <Tag className={className}>{children}</Tag>;
}

function parseMathSegments(text: string): Segment[] {
  const segments: Segment[] = [];
  let index = 0;

  while (index < text.length) {
    const next = findNextDelimiter(text, index);
    if (!next) {
      pushText(segments, text.slice(index));
      break;
    }

    const { delimiter, position } = next;
    const end = findDelimiterEnd(text, position + delimiter.start.length, delimiter.end);
    if (end === -1) {
      pushText(segments, text.slice(index));
      break;
    }

    pushText(segments, text.slice(index, position));
    segments.push({
      type: "math",
      value: text.slice(position + delimiter.start.length, end).trim(),
      display: delimiter.display,
    });
    index = end + delimiter.end.length;
  }

  return segments;
}

function findNextDelimiter(text: string, startIndex: number): { delimiter: Delimiter; position: number } | null {
  let match: { delimiter: Delimiter; position: number } | null = null;

  for (const delimiter of DELIMITERS) {
    let position = text.indexOf(delimiter.start, startIndex);
    while (position !== -1 && (!canOpenDelimiter(text, position, delimiter) || isEscaped(text, position))) {
      position = text.indexOf(delimiter.start, position + delimiter.start.length);
    }

    if (
      position !== -1 &&
      (!match ||
        position < match.position ||
        (position === match.position && delimiter.start.length > match.delimiter.start.length))
    ) {
      match = { delimiter, position };
    }
  }

  return match;
}

function findDelimiterEnd(text: string, startIndex: number, delimiter: string): number {
  let position = text.indexOf(delimiter, startIndex);
  while (position !== -1 && isEscaped(text, position)) {
    position = text.indexOf(delimiter, position + delimiter.length);
  }
  return position;
}

function canOpenDelimiter(text: string, position: number, delimiter: Delimiter): boolean {
  if (delimiter.start !== "$") {
    return true;
  }

  const next = text[position + 1];
  return Boolean(next && !/\s|\d/.test(next));
}

function isEscaped(text: string, position: number): boolean {
  let slashCount = 0;
  for (let cursor = position - 1; cursor >= 0 && text[cursor] === "\\"; cursor -= 1) {
    slashCount += 1;
  }
  return slashCount % 2 === 1;
}

function pushText(segments: Segment[], value: string) {
  if (!value) {
    return;
  }
  const previous = segments[segments.length - 1];
  if (previous?.type === "text") {
    previous.value += value;
  } else {
    segments.push({ type: "text", value });
  }
}
