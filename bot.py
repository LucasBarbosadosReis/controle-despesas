import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from collections.abc import Iterable

from dotenv import load_dotenv
from flask import Flask, Response, request
from sqlalchemy import func, select
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

MESSAGE_PATTERN = re.compile(r"^(?P<description>.+?)\s+(?P<amount>\d+(?:[.,]\d{1,2})?)$")


def parse_expense(message: str) -> tuple[str, Decimal]:
    """Parse a message such as 'Uber 15' or 'Almoco 15,50'."""
    match = MESSAGE_PATTERN.fullmatch(message.strip())
    if match is None:
        raise ValueError("Formato inválido. Envia uma descrição e um valor, por exemplo: Uber 15")

    description = match.group("description").strip()
    try:
        amount = Decimal(match.group("amount").replace(",", "."))
    except InvalidOperation as error:
        raise ValueError("O valor da despesa não é válido.") from error

    if not description or not amount.is_finite() or amount <= 0:
        raise ValueError("A descrição e o valor têm de ser válidos; o valor deve ser maior que zero.")
    return description, amount


def calculate_month_total(values: Iterable[Decimal | float | int]) -> Decimal:
    """Sum expense values using decimal arithmetic to avoid float rounding."""
    return sum((Decimal(str(value)) for value in values), start=Decimal(0))


def save_expense(description: str, amount: Decimal) -> Decimal:
    """Persist an expense and return the current month's total."""
    from banco import Despesa, SessionLocal

    today = date.today()  # noqa: DTZ011
    month_start = today.replace(day=1)
    next_month = date(today.year + (today.month == 12), today.month % 12 + 1, 1)

    with SessionLocal() as session:
        session.add(Despesa(descricao=description, valor=float(amount), data=today))
        session.commit()
        total = session.scalar(
            select(func.coalesce(func.sum(Despesa.valor), 0)).where(
                Despesa.data >= month_start,
                Despesa.data < next_month,
            )
        )
    return Decimal(str(total or 0))


def _reply(message: str) -> Response:
    twiml = MessagingResponse()
    twiml.message(message)
    return Response(str(twiml), mimetype="application/xml")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/whatsapp")
def whatsapp_webhook() -> Response:
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    signature = request.headers.get("X-Twilio-Signature", "")
    validator = RequestValidator(auth_token or "")
    if not auth_token or not validator.validate(request.url, request.form, signature):
        return Response("Invalid Twilio signature", status=403)

    try:
        description, amount = parse_expense(request.form.get("Body", ""))
        month_total = save_expense(description, amount)
    except ValueError as error:
        return _reply(str(error))
    except Exception:
        app.logger.exception("Failed to save incoming WhatsApp expense")
        return _reply("Não foi possível guardar a despesa agora. Tenta novamente mais tarde.")

    response = (
        f"✅ Despesa '{description}' de R$ {amount:.2f} guardada! "
        f"O teu gasto total neste mês agora é R$ {month_total:.2f}."
    )
    return _reply(response)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))