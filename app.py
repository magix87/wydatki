from flask import Flask, render_template, request, redirect, session
from models import db, Expense
from datetime import datetime
import calendar
from collections import defaultdict
from collections import defaultdict
from datetime import datetime, timedelta
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)
app.secret_key = 'supersekretnyklucz'  # ustaw coś losowego i trudnego
app.permanent_session_lifetime = timedelta(minutes=10)  # ile trwa sesja
with app.app_context():
    db.create_all()


def get_month_name(month_number):
    return calendar.month_name[month_number]  # np. 7 → "July"


@app.route('/', methods=['GET', 'POST'])
def welcome():
    if request.method == 'POST':
        pin = request.form.get('pin')
        if pin == '1126':
            session.permanent = True  # <-- TO DODAJ
            session['authenticated'] = True
            return redirect('/wydatki')
        else:
            return render_template('welcome.html', error="Błędny PIN")
    return render_template('welcome.html')

@app.route('/wydatki')
def index():
    if not session.get('authenticated'):
        return redirect('/')
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)

    expenses = Expense.query.filter(
        db.extract('month', Expense.date) == month,
        db.extract('year', Expense.date) == year
    ).order_by(Expense.date.desc()).all()

    adam_sum = sum(e.amount for e in expenses if e.person == 'Adam')
    malwina_sum = sum(e.amount for e in expenses if e.person == 'Malwina')
    month_total = adam_sum + malwina_sum

    if adam_sum > malwina_sum:
        who_spent_more = f"💰 Adam wydał więcej o {adam_sum - malwina_sum:.2f} PLN"
    elif malwina_sum > adam_sum:
        who_spent_more = f"💸 Malwina wydała więcej o {malwina_sum - adam_sum:.2f} PLN"
    else:
        who_spent_more = "🤝 Oboje wydali tyle samo"

    # 🔢 Przygotowanie danych do wykresu miesięcznego (np. ostatnie 6 miesięcy)
    month_labels = []
    adam_totals = []
    malwina_totals = []

    category_sums = defaultdict(float)
    for e in expenses:
        category_sums[e.category] += e.amount

    category_labels = list(category_sums.keys())
    category_values = list(category_sums.values())

    today = datetime.now()
    for i in range(5, -1, -1):  # ostatnie 6 miesięcy
        target = today - timedelta(days=30 * i)
        m, y = target.month, target.year
        monthly_expenses = Expense.query.filter(
            db.extract('month', Expense.date) == m,
            db.extract('year', Expense.date) == y
        ).all()
        month_labels.append(target.strftime('%b %Y'))  # np. "Jul 2025"
        adam_totals.append(sum(e.amount for e in monthly_expenses if e.person == 'Adam'))
        malwina_totals.append(sum(e.amount for e in monthly_expenses if e.person == 'Malwina'))

    return render_template(
        'index.html',
        expenses=expenses,
        adam_sum=adam_sum,
        malwina_sum=malwina_sum,
        month=month,
        year=year,
        who_spent_more=who_spent_more,
        month_name=calendar.month_name[month],
        chart_labels=month_labels,
        chart_adam=adam_totals,
        chart_malwina=malwina_totals,
        month_total=month_total,
        category_labels=category_labels,
        category_values=category_values
    )


@app.route('/add', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        date_input = request.form['date']
        try:
            parsed_date = datetime.strptime(date_input, '%Y-%m-%d')
        except ValueError:
            parsed_date = datetime.utcnow()

        new_expense = Expense(
            person=request.form['person'],
            category=request.form['category'],
            amount=float(request.form['amount']),
            description=request.form['description'],
            date=parsed_date
        )
        db.session.add(new_expense)
        db.session.commit()
        return redirect('/')

    return render_template('add.html')  # <-- TYLKO TO tu zostaje
@app.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)

    if request.method == 'POST':
        expense.person = request.form['person']
        expense.category = request.form['category']
        expense.amount = float(request.form['amount'])
        expense.description = request.form['description']
        try:
            expense.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        except ValueError:
            pass  # nie zmieniaj daty jeśli błędna
        db.session.commit()
        return redirect('/')

    return render_template('edit.html', expense=expense)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
