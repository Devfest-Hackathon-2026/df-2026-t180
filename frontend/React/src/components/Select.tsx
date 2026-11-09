import {
  forwardRef,
  type KeyboardEvent,
  useEffect,
  useId,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { Icon } from "./Icon";
import styles from "./Select.module.css";

export type SelectOption = { value: string; label: string };

type Props = {
  id: string;
  value: string;
  options: SelectOption[];
  placeholder: string;
  onChange: (value: string) => void;
  invalid?: boolean;
  describedBy?: string;
  labelledBy: string;
};

/**
 * Single-choice dropdown that opens directly under the field, in the app's own style. The native
 * select menu is drawn by the OS (on macOS it opens on top of the field) and cannot be styled.
 * Follows the ARIA "select-only combobox" pattern: arrows, Home/End, Enter, Escape, type to jump.
 */
export const Select = forwardRef<{ focus: () => void }, Props>(function Select(props, ref) {
  const { id, value, options, placeholder, onChange, invalid, describedBy, labelledBy } = props;
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const listId = useId();
  const selected = options.find((option) => option.value === value);

  useImperativeHandle(ref, () => ({ focus: () => buttonRef.current?.focus() }));

  // Close when clicking or tapping anywhere outside.
  useEffect(() => {
    if (!open) return;
    const onDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [open]);

  function show() {
    setActive(
      Math.max(
        0,
        options.findIndex((option) => option.value === value),
      ),
    );
    setOpen(true);
  }

  function choose(index: number) {
    const option = options[index];
    if (option) onChange(option.value);
    setOpen(false);
    buttonRef.current?.focus();
  }

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    const last = options.length - 1;
    const keys: Record<string, () => void> = {
      ArrowDown: () => (open ? setActive((i) => Math.min(last, i + 1)) : show()),
      ArrowUp: () => (open ? setActive((i) => Math.max(0, i - 1)) : show()),
      Home: () => open && setActive(0),
      End: () => open && setActive(last),
      Enter: () => (open ? choose(active) : show()),
      " ": () => (open ? choose(active) : show()),
      Escape: () => setOpen(false),
      Tab: () => setOpen(false),
    };
    const action = keys[event.key];
    if (action) {
      if (event.key !== "Tab") event.preventDefault();
      action();
      return;
    }
    // Type a letter to jump to the first option starting with it.
    if (event.key.length === 1) {
      const index = options.findIndex((option) =>
        option.label.toLowerCase().startsWith(event.key.toLowerCase()),
      );
      if (index >= 0) {
        if (open) setActive(index);
        else onChange(options[index].value);
      }
    }
  }

  return (
    <div ref={rootRef} className={styles.root} data-open={open || undefined}>
      <button
        ref={buttonRef}
        id={id}
        type="button"
        className={styles.field}
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-labelledby={`${labelledBy} ${id}`}
        aria-activedescendant={open ? `${listId}-${active}` : undefined}
        aria-invalid={invalid || undefined}
        aria-describedby={describedBy}
        onClick={() => (open ? setOpen(false) : show())}
        onKeyDown={onKeyDown}
      >
        <span className={styles.value} data-placeholder={!selected || undefined}>
          {selected?.label ?? placeholder}
        </span>
        <span className={styles.chevron} aria-hidden="true">
          <Icon name="arrow" size={18} />
        </span>
      </button>

      {open && (
        <ul className={styles.list} id={listId} role="listbox" aria-labelledby={labelledBy}>
          {options.map((option, index) => (
            <li
              key={option.value}
              id={`${listId}-${index}`}
              role="option"
              className={styles.option}
              aria-selected={option.value === value}
              data-active={index === active || undefined}
              onPointerEnter={() => setActive(index)}
              onClick={() => choose(index)}
            >
              <span>{option.label}</span>
              {option.value === value && (
                <span className={styles.check} aria-hidden="true">
                  <Icon name="check" size={18} strokeWidth={2.4} />
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
});
