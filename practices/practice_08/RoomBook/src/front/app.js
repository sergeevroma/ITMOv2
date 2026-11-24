const ui = {
  form: document.querySelector("#booking-form"),
  fields: document.querySelector("#booking-fields"),
  submitLabel: document.querySelector("#submit-label"),
  submitSpinner: document.querySelector("#submit-spinner"),
  formError: document.querySelector("#form-error"),
  success: document.querySelector("#action-success"),
  actionError: document.querySelector("#action-error"),
  date: document.querySelector("#booking-date"),
  rooms: document.querySelector("#room-picker"),
  start: document.querySelector("#booking-start"),
  end: document.querySelector("#booking-end"),
  bookingHours: document.querySelector("#booking-hours"),
  configLoading: document.querySelector("#config-loading"),
  configError: document.querySelector("#config-error"),
  configRetry: document.querySelector("#config-retry"),
  schedule: document.querySelector("#schedule-panel"),
  scheduleDate: document.querySelector("#schedule-date"),
  scheduleHours: document.querySelector("#schedule-hours"),
  filter: document.querySelector("#schedule-room"),
  count: document.querySelector("#booking-count"),
  list: document.querySelector("#booking-list"),
  loading: document.querySelector("#schedule-loading"),
  empty: document.querySelector("#schedule-empty"),
  emptyTitle: document.querySelector("#empty-title"),
  emptyMessage: document.querySelector("#empty-message"),
  error: document.querySelector("#schedule-error"),
  retry: document.querySelector("#schedule-retry"),
  footer: document.querySelector("#schedule-footer"),
  hintTitle: document.querySelector("#schedule-hint-title"),
};

let rules = null;
let pendingSchedule = null;
let saving = false;
let lastCreatedId = null;
const cancelling = new Set();

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error = new Error(body?.error?.message || `HTTP ${response.status}`);
    error.status = response.status;
    error.fields = body?.error?.fields || {};
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

function cloneTemplate(id) {
  return document.querySelector(id).content.firstElementChild.cloneNode(true);
}

function renderRooms(rooms) {
  const choices = [];
  const filters = [new Option("Все комнаты", "")];
  for (const room of rooms) {
    const choice = cloneTemplate("#room-template");
    const radio = choice.querySelector("input");
    radio.value = room.id;
    radio.setAttribute("aria-label", room.name);
    radio.setAttribute("aria-describedby", "room-error");
    choice.querySelector(".room-number").textContent = room.id;
    choice.querySelector(".room-capacity").textContent = `Мест: ${room.capacity}`;
    choice.querySelector(".room-equipment").textContent = room.equipment.join(", ");
    choices.push(choice);
    filters.push(new Option(room.name, room.id));
  }
  ui.rooms.replaceChildren(...choices);
  ui.filter.replaceChildren(...filters);
  ui.filter.disabled = false;
}

function toMinutes(value) {
  const [hours, minutes] = value.split(":").map(Number);
  return hours * 60 + minutes;
}

function formatTime(minutes) {
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

function renderTimeOptions() {
  const opening = toMinutes(rules.opens_at);
  const closing = toMinutes(rules.closes_at);
  for (const select of [ui.start, ui.end]) {
    const placeholder = new Option("Выберите", "", true, true);
    placeholder.disabled = true;
    select.replaceChildren(placeholder);
    select.disabled = false;
  }
  for (let minute = opening; minute <= closing; minute += rules.slot_minutes) {
    const time = formatTime(minute);
    if (minute < closing) ui.start.add(new Option(time, time));
    if (minute > opening) ui.end.add(new Option(time, time));
  }
  ui.bookingHours.textContent = `С ${rules.opens_at} до ${rules.closes_at}, интервал — ${rules.slot_minutes} минут.`;
  ui.scheduleHours.textContent = `${rules.opens_at}–${rules.closes_at}`;
}

function todayInTimezone(timezone) {
  const formatter = new Intl.DateTimeFormat("en", {
    timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit",
  });
  const parts = Object.fromEntries(formatter.formatToParts(new Date()).map(part => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function updateScheduleDate(day) {
  if (!day) {
    ui.scheduleDate.textContent = "Дата не выбрана";
    return;
  }
  const label = new Intl.DateTimeFormat("ru-RU", {
    timeZone: "UTC", weekday: "long", day: "numeric", month: "long",
  }).format(new Date(`${day}T12:00:00Z`));
  ui.scheduleDate.textContent = label[0].toUpperCase() + label.slice(1);
}

function showScheduleState(state) {
  ui.loading.hidden = state !== "loading";
  ui.error.hidden = state !== "error";
  ui.empty.hidden = state !== "empty" && state !== "date-required";
  ui.list.hidden = state !== "ready";
  ui.footer.hidden = state !== "ready" && state !== "empty";
  ui.schedule.setAttribute("aria-busy", String(state === "loading"));
  if (state !== "ready") {
    ui.list.replaceChildren();
    ui.count.textContent = state === "empty" ? "0 броней" : "—";
  }
  ui.emptyTitle.textContent = state === "date-required" ? "Выберите дату" : "Пока нет броней";
  ui.emptyMessage.textContent = state === "date-required"
    ? "Укажите дату в шапке, чтобы увидеть расписание."
    : "Для выбранной даты и фильтра бронирований нет.";
}

function createBookingCard(booking) {
  const card = cloneTemplate("#booking-template");
  const organizer = card.querySelector(".meeting-organizer");
  organizer.id = `meeting-${booking.id}`;
  card.setAttribute("aria-labelledby", organizer.id);
  card.querySelector(".room-badge").textContent = `Комната ${booking.room_id}`;
  for (const field of ["start", "end"]) {
    const time = card.querySelector(`[data-time="${field}"]`);
    time.dateTime = booking[field];
    time.textContent = booking[field];
  }
  organizer.textContent = booking.organizer;
  card.querySelector(".meeting-description").textContent = booking.title;
  card.classList.toggle("new-booking", booking.id === lastCreatedId);
  const cancel = card.querySelector("button");
  cancel.disabled = cancelling.has(booking.id);
  cancel.textContent = cancel.disabled ? "Отменяем…" : "Отменить";
  cancel.setAttribute(
    "aria-label", `Отменить бронь комнаты ${booking.room_id} на ${booking.start}`,
  );
  cancel.addEventListener("click", () => cancelBooking(booking, cancel));
  return card;
}

function renderSchedule(bookings) {
  ui.list.replaceChildren(...bookings.map(createBookingCard));
  showScheduleState(bookings.length ? "ready" : "empty");
  const word = { one: "бронь", few: "брони", many: "броней", other: "броней" };
  ui.count.textContent = `${bookings.length} ${word[new Intl.PluralRules("ru").select(bookings.length)]}`;
  if (bookings.length) {
    ui.hintTitle.textContent = ui.filter.value
      ? "В остальное время выбранная комната свободна"
      : "В остальное время комнаты свободны";
  } else {
    const subject = ui.filter.value ? "Выбранная комната свободна" : "Все комнаты свободны";
    ui.hintTitle.textContent = `${subject} с ${rules.opens_at} до ${rules.closes_at}`;
  }
}

async function loadSchedule() {
  if (!rules) return;
  pendingSchedule?.abort();
  const controller = new AbortController();
  pendingSchedule = controller;
  const day = ui.date.value;
  updateScheduleDate(day);
  if (!day || !ui.date.validity.valid) {
    showScheduleState("date-required");
    return;
  }
  showScheduleState("loading");
  const query = new URLSearchParams({ date: day });
  if (ui.filter.value) query.set("room_id", ui.filter.value);
  try {
    const bookings = await fetchJson(`/api/bookings?${query}`, { signal: controller.signal });
    if (!controller.signal.aborted) renderSchedule(bookings);
  } catch (error) {
    if (!controller.signal.aborted) showScheduleState("error");
  }
}

async function initialize() {
  ui.configLoading.hidden = false;
  ui.configError.hidden = true;
  ui.configRetry.disabled = true;
  try {
    const [rooms, bookingRules] = await Promise.all([
      fetchJson("/api/rooms"), fetchJson("/api/booking-rules"),
    ]);
    rules = bookingRules;
    renderRooms(rooms);
    renderTimeOptions();
    ui.date.value ||= todayInTimezone(rules.timezone);
    ui.date.disabled = false;
    ui.fields.disabled = false;
    ui.configLoading.hidden = true;
    await loadSchedule();
  } catch (error) {
    ui.configError.hidden = false;
  } finally {
    ui.configLoading.hidden = true;
    ui.configRetry.disabled = false;
  }
}

function controlsFor(name) {
  return [...ui.form.elements].filter(control => control.name === name);
}

function clearFieldError(name) {
  const feedback = [...document.querySelectorAll("[data-field-error]")]
    .find(element => element.dataset.fieldError === name);
  if (feedback) feedback.hidden = true;
  for (const control of controlsFor(name)) {
    control.classList.remove("is-invalid");
    control.removeAttribute("aria-invalid");
  }
}

function clearFormErrors() {
  for (const feedback of document.querySelectorAll("[data-field-error]")) {
    clearFieldError(feedback.dataset.fieldError);
  }
  ui.formError.hidden = true;
}

function showFormErrors(fields, message = "Проверьте выделенные поля.") {
  let firstControl = null;
  for (const feedback of document.querySelectorAll("[data-field-error]")) {
    const name = feedback.dataset.fieldError;
    if (!fields[name]) continue;
    feedback.textContent = fields[name];
    feedback.hidden = false;
    for (const control of controlsFor(name)) {
      control.classList.add("is-invalid");
      control.setAttribute("aria-invalid", "true");
      firstControl ||= control;
    }
  }
  ui.formError.textContent = fields._form || message;
  ui.formError.hidden = false;
  (firstControl || ui.formError).focus();
}

function validateBooking(booking) {
  const errors = {};
  if (!booking.room_id) errors.room_id = "Выберите комнату.";
  if (!booking.date || !ui.date.validity.valid) errors.date = "Укажите дату бронирования.";
  for (const [name, limit] of [["organizer", 80], ["title", 120]]) {
    if (!booking[name]) errors[name] = "Заполните поле.";
    else if (booking[name].length > limit) errors[name] = `Не более ${limit} символов.`;
  }
  for (const name of ["start", "end"]) {
    if (!booking[name]) errors[name] = "Выберите время.";
  }
  if (booking.start && booking.end && booking.end <= booking.start) {
    errors.end = "Окончание должно быть позже начала.";
  }
  return errors;
}

function setSaving(value) {
  saving = value;
  ui.fields.disabled = value;
  ui.date.disabled = value;
  ui.form.setAttribute("aria-busy", String(value));
  ui.submitSpinner.hidden = !value;
  ui.submitLabel.textContent = value ? "Бронируем…" : "Забронировать";
}

async function submitBooking(event) {
  event.preventDefault();
  if (!rules || saving) return;
  clearFormErrors();
  ui.success.hidden = true;
  ui.actionError.hidden = true;
  const data = Object.fromEntries(new FormData(ui.form));
  const booking = {
    room_id: Number(data.room_id), date: data.date,
    organizer: data.organizer.trim(), title: data.title.trim(),
    start: data.start, end: data.end,
  };
  const errors = validateBooking(booking);
  if (Object.keys(errors).length) {
    showFormErrors(errors);
    return;
  }
  setSaving(true);
  let created;
  try {
    created = await fetchJson("/api/bookings", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(booking),
    });
  } catch (error) {
    setSaving(false);
    const message = error.status === 409 || error.status === 422
      ? error.message
      : "Не удалось получить подтверждение. Обновите расписание перед повторной отправкой: бронь могла сохраниться.";
    showFormErrors(error.fields || {}, message);
    return;
  }
  // reset() сбрасывает и дату в шапке: она тоже связана с этой формой.
  ui.form.reset();
  ui.date.value = created.date;
  ui.filter.value = "";
  lastCreatedId = created.id;
  setSaving(false);
  ui.success.textContent = `Бронь создана: комната ${created.room_id}, ${created.date}, ${created.start}–${created.end}.`;
  ui.success.hidden = false;
  controlsFor("room_id")[0]?.focus();
  await loadSchedule();
}

async function cancelBooking(booking, button) {
  if (cancelling.has(booking.id)) return;
  cancelling.add(booking.id);
  button.disabled = true;
  button.textContent = "Отменяем…";
  ui.success.hidden = true;
  ui.actionError.hidden = true;
  try {
    await fetchJson(`/api/bookings/${booking.id}`, { method: "DELETE" });
    ui.success.textContent = `Бронь отменена: комната ${booking.room_id}, ${booking.date}, ${booking.start}–${booking.end}.`;
    ui.success.hidden = false;
    if (document.activeElement === button) ui.filter.focus();
    await loadSchedule();
  } catch (error) {
    ui.actionError.textContent = error.status === 404
      ? "Эта бронь уже отменена. Расписание обновлено."
      : "Не удалось отменить бронь. Повторите отмену или обновите расписание, чтобы проверить её состояние.";
    ui.actionError.hidden = false;
    ui.actionError.focus();
    if (error.status === 404) await loadSchedule();
  } finally {
    cancelling.delete(booking.id);
    // Карточка могла быть заменена обновлением расписания во время запроса.
    const current = document.querySelector(`#meeting-${booking.id}`)?.closest("article").querySelector("button");
    if (current) {
      current.disabled = false;
      current.textContent = "Отменить";
    }
  }
}

ui.date.addEventListener("change", loadSchedule);
ui.filter.addEventListener("change", loadSchedule);
ui.retry.addEventListener("click", loadSchedule);
ui.configRetry.addEventListener("click", initialize);
ui.form.addEventListener("submit", submitBooking);
for (const target of [ui.form, ui.date]) {
  target.addEventListener("input", event => {
    clearFieldError(event.target.name);
    if (event.target.name === "start") clearFieldError("end");
  });
}
initialize();
