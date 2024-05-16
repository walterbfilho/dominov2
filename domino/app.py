import base64
import os
from datetime import datetime, timedelta
from io import BytesIO
from operator import itemgetter
import calendar
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   url_for)
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from sqlalchemy import and_
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from wtforms import (BooleanField, DateField, IntegerField, PasswordField,
                     SelectField, SelectMultipleField, StringField,
                     SubmitField)
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
load_dotenv()
#print(f"MYSQL AQUI O --> mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}")
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class LoginForm(FlaskForm):
    username = StringField('Nome do Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Nome do Usuário', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    #image = FileField('Imagem', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    password2 = PasswordField('Confirme a sua senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')
        
login = LoginManager(app)
login.login_view = 'login'

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

#@app.route('/register', methods=['GET', 'POST'])
#def register():
#    if current_user.is_authenticated:
#        return redirect(url_for('home'))
#    form = RegistrationForm()
#    if form.validate_on_submit():
#        user = User(username=form.username.data, email=form.email.data)
#        user.set_password(form.password.data)
#        db.session.add(user)
#        db.session.commit()
#        return redirect(url_for('login'))
#    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    mensagem_erro = ''
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            mensagem_erro = 'Nome e/ou senha incorreto(s).'
        else:
            login_user(user)
            return redirect(url_for('home'))
    return render_template('login.html', title='Sign In', form=form, mensagem_erro=mensagem_erro)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))
    
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    points = db.Column(db.Integer, nullable=False, default=0)
    buchos_dados = db.Column(db.Integer, nullable=False, default=0)
    buchos_recebidos = db.Column(db.Integer, nullable=False, default=0)
    frequencia_dias = db.Column(db.Integer, nullable=False, default=0)
    image_filename = db.Column(db.String(120), nullable=True)
    game_day_details = db.relationship("GameDayPlayerDetails", back_populates="player")

class PlayerForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired()])
    image = FileField('Imagem', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    points = IntegerField('Pontos', default=0)
    frequencia_dias = IntegerField('Frequência', default=0)
    buchos_dados = IntegerField('Buchos dados', default=0)
    buchos_recebidos = IntegerField('Buchos recebidos', default=0)
    submit = SubmitField('Registrar')
    def set_submit_label(self, label):
        self.submit.label.text = label

class GameDay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    player_details = db.relationship("GameDayPlayerDetails", back_populates="game_day")

class GameDayForm(FlaskForm):
    date = DateField('Data do Jogo', format='%Y-%m-%d', validators=[DataRequired()])
    player_ids = SelectMultipleField('Jogadores', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Registrar')

class BuchosForm(FlaskForm):
    buchos_given = IntegerField('Buchos Dados', default=0)
    buchos_received = IntegerField('Buchos Recebidos', default=0)
    submit = SubmitField('Atualizar')

@app.route('/chart')
def chart():
    players = Player.query.all()
    names = [player.name for player in players]
    points = [player.points for player in players]
    frequencia_dias = [player.frequencia_dias for player in players]
    buchos_dados = [player.buchos_dados/fd if fd != 0 else 0 for player, fd in zip(players, frequencia_dias)]
    buchos_recebidos = [player.buchos_recebidos/fd if fd != 0 else 0 for player, fd in zip(players, frequencia_dias)]
    image_filename = [player.image_filename for player in players]

    if players:
        average_buchos_dados = [bd/fd if fd != 0 else 0 for bd, fd in zip(buchos_dados, frequencia_dias)]
        average_buchos_recebidos = [br/fd if fd != 0 else 0 for br, fd in zip(buchos_recebidos, frequencia_dias)]
        max_points_player = names[points.index(max(points))]
        max_frequencia_dias_player = names[frequencia_dias.index(max(frequencia_dias))]
        max_buchos_dados_player = names[average_buchos_dados.index(max(average_buchos_dados))]
        max_buchos_recebidos_player = names[average_buchos_recebidos.index(max(average_buchos_recebidos))]
        max_points_image = image_filename[points.index(max(points))]
        max_frequencia_dias_image = image_filename[frequencia_dias.index(max(frequencia_dias))]
        max_buchos_dados_image = image_filename[average_buchos_dados.index(max(average_buchos_dados))]
        max_buchos_recebidos_image = image_filename[average_buchos_recebidos.index(max(average_buchos_recebidos))]
    else:
        max_points_player = 0
        max_frequencia_dias_player = 0
        max_buchos_dados_player = 0
        max_buchos_recebidos_player = 0
        max_points_image = 0
        max_frequencia_dias_image = 0
        max_buchos_dados_image = 0
        max_buchos_recebidos_image = 0

    return render_template(
        'chart.html', 
        frequencia_dias=frequencia_dias, 
        names=names, 
        points=points, 
        buchos_dados=buchos_dados, 
        buchos_recebidos=buchos_recebidos,
        image_filename=image_filename,
        max_points_image=max_points_image,
        max_frequencia_dias_image=max_frequencia_dias_image,
        max_buchos_dados_image=max_buchos_dados_image,
        max_buchos_recebidos_image=max_buchos_recebidos_image,
        max_points_player=max_points_player,
        max_frequencia_dias_player=max_frequencia_dias_player,
        max_buchos_dados_player=max_buchos_dados_player,
        max_buchos_recebidos_player=max_buchos_recebidos_player,
        players = players
    )

from datetime import datetime, timedelta


@app.route('/reset_monthly_values', methods=['POST'])
def reset_monthly_values():
    if datetime.now().day == 1:
        players = Player.query.all()
        for player in players:
            player.points = 0
            player.buchos_recebidos = 0
            player.buchos_dados = 0

        db.session.commit()
    return redirect(url_for('home'))

#def schedule_reset():
#    scheduler = BackgroundScheduler()
#    scheduler.add_job(reset_monthly_values, 'interval', days=1)  # A cada 4 semanas
#    scheduler.start()

class GameDayPlayerDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_day_id = db.Column(db.Integer, db.ForeignKey('game_day.id'))
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    buchos_given = db.Column(db.Integer, default=0)
    buchos_received = db.Column(db.Integer, default=0)
    game_day = db.relationship("GameDay", back_populates="player_details")
    player = db.relationship("Player", back_populates="game_day_details")

@app.route('/update_buchos/<int:game_day_id>/<int:player_id>', methods=['GET', 'POST'])
def update_buchos(game_day_id, player_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    form = BuchosForm()
    detail = GameDayPlayerDetails.query.filter_by(game_day_id=game_day_id, player_id=player_id).first()

    if form.validate_on_submit():
        if not detail:
            detail = GameDayPlayerDetails(game_day_id=game_day_id, player_id=player_id)
            db.session.add(detail)

        detail.player.points -= detail.buchos_given * 100
        detail.player.points += detail.buchos_received * 150
        detail.player.points += form.buchos_given.data * 100
        detail.player.points -= form.buchos_received.data * 150
        detail.player.buchos_dados -= detail.buchos_given
        detail.player.buchos_recebidos -= detail.buchos_received
        detail.player.buchos_dados += form.buchos_given.data
        detail.player.buchos_recebidos += form.buchos_received.data
        detail.buchos_given = form.buchos_given.data
        detail.buchos_received = form.buchos_received.data
        db.session.commit()
        return redirect(url_for('view_game_day', game_day_id=game_day_id))
    else:
        form.buchos_given.data = detail.buchos_given
        form.buchos_received.data = detail.buchos_received

    return render_template('update_buchos.html', form=form, detail=detail)

@app.route('/player/<int:player_id>')
def view_player(player_id):
    player = Player.query.get_or_404(player_id)
    return render_template('player_details.html', player=player)

@app.route('/view_game_day/<int:game_day_id>')
def view_game_day(game_day_id):
    gameDay = GameDay.query.get_or_404(game_day_id)
    gameDayPlayerDetails = GameDayPlayerDetails.query.filter_by(game_day_id=game_day_id).all()

    return render_template('view_game_day.html', gameDay=gameDay, gameDayPlayerDetails=gameDayPlayerDetails)

@app.route('/game_days', methods=['GET', 'POST'])
def view_game_days():
    form = GameDayForm()
    form.player_ids.choices = [(player.id, player.name) for player in Player.query.all()]
    print('to aqui 1')
    if form.validate_on_submit():
        print('to aqui 1')
        game_day = GameDay(date=form.date.data)
        db.session.add(game_day)
        db.session.flush()
        allplayers = Player.query.all()
        selected_players = Player.query.filter(Player.id.in_(form.player_ids.data)).all()

        for player in selected_players:
            print('to aqui 2')
            player.points += 100
            player.frequencia_dias += 1
            detail = GameDayPlayerDetails.query.filter_by(game_day=game_day, player=player).first()
            if not detail:
                detail = GameDayPlayerDetails(game_day=game_day, player=player)
                db.session.add(detail)

        for player in allplayers:
            if player not in selected_players:
                player.points -= 100

        game_day.players = selected_players
        db.session.add(game_day)
        db.session.commit()
        return redirect(url_for('view_game_days'))
    
    if(form.errors):
        print(f'ERRO NO FORM: {form.errors}')
    
    game_days = GameDay.query.order_by(GameDay.date.desc()).all()
    return render_template('game_days.html', game_days=game_days, form=form)

class RelatorioForm(FlaskForm):
    de = SelectField('De', coerce=str, choices=[], validators=[DataRequired()])
    ate = SelectField('Até', coerce=str, choices=[], validators=[DataRequired()])
    submit = SubmitField('Buscar')

@app.route('/relatorio_anos', methods=['GET', 'POST'])
def relatorio_anos():
    game_days = GameDay.query.order_by(GameDay.date.asc()).all()
    anos_disponiveis = set(f'{gd.date.month}/{gd.date.year}' for gd in game_days)
    options = [(ano, str(ano)) for ano in anos_disponiveis]
    ate_select = 0
    form = RelatorioForm()
    form.de.choices = [('', 'Nenhum')] + options
    form.ate.choices = [('', 'Nenhum')] + options

    player_stats = {}
    if form.validate_on_submit():
        mes_inicio, ano_inicio = map(int, form.de.data.split('/'))
        mes_fim, ano_fim = map(int, form.ate.data.split('/'))
        
        data_inicio = datetime(ano_inicio, mes_inicio, 1)
        data_fim = datetime(ano_fim, mes_fim, 1) + timedelta(days=31)
        
        game_days_intervalo = GameDay.query.filter(GameDay.date > data_inicio, GameDay.date < data_fim).all()
        for gd in game_days_intervalo:
            details = GameDayPlayerDetails.query.filter_by(game_day_id=gd.id).all()
            for detail in details:
                player_id = detail.player_id
                if player_id not in player_stats:
                    player_info = Player.query.get(player_id)
                    player_stats[player_id] = {
                        'name': player_info.name,
                        'buchos_dados': 0,
                        'buchos_recebidos': 0,
                        'frequencia': 0
                    }
                player_stats[player_id]['buchos_dados'] += detail.buchos_given
                player_stats[player_id]['buchos_recebidos'] += detail.buchos_received
                player_stats[player_id]['frequencia'] += 1

        ordenacao = request.form.get('ordenacao')  
        if ordenacao == 'buchos_dados':
            player_stats = dict(sorted(player_stats.items(), key=lambda x: x[1]['buchos_dados'], reverse=True))
        elif ordenacao == 'buchos_recebidos':
            player_stats = dict(sorted(player_stats.items(), key=lambda x: x[1]['buchos_recebidos'], reverse=True))

        ate_select = 1

    return render_template('relatorio_anos.html', form=form, ate_select=ate_select, player_stats=player_stats)

@app.route('/')
def home():
    order_by = request.args.get('order_by', 'points')
    order_type = request.args.get('order_type', 'desc') 

    if order_by not in ['name', 'points', 'frequencia_dias', 'buchos_dados', 'buchos_recebidos']:
        order_by = 'points'
    
    if order_type not in ['asc', 'desc']:
        order_type = 'desc'  

    if order_type == 'desc':
        players = Player.query.order_by(getattr(Player, order_by).desc()).all()
    else:
        players = Player.query.order_by(getattr(Player, order_by).asc()).all()
    
    game_days = GameDay.query.order_by(GameDay.date.desc()).all()
    
    data_atual = datetime.now()
    primeiro_dia_mes = data_atual.replace(day=1)

    ultimo_dia_mes = primeiro_dia_mes.replace(day=calendar.monthrange(data_atual.year, data_atual.month)[1])
    game_days_intervalo = GameDay.query.filter(GameDay.date >= primeiro_dia_mes, GameDay.date <= ultimo_dia_mes).all()

    player_stats = {}

    for gd in game_days_intervalo:
        print(f'GameDay: --> {gd.date}')
        details = GameDayPlayerDetails.query.filter_by(game_day_id=gd.id).all()
        for detail in details:
            player_id = detail.player_id
            if player_id not in player_stats:
                player_info = Player.query.get(player_id)
                player_stats[player_id] = {
                    'name': player_info.name,
                    'image_filename': player_info.image_filename,
                    'buchos_dados': 0,
                    'buchos_recebidos': 0,
                    'frequencia': 0
                }
            player_stats[player_id]['buchos_dados'] += detail.buchos_given
            player_stats[player_id]['buchos_recebidos'] += detail.buchos_received
            player_stats[player_id]['frequencia'] += 1

    top_buchos_dados_ord = sorted(player_stats.items(), key=lambda x: x[1]['buchos_dados'], reverse=True)[:3]
    top_buchos_dados = [{'id': pid, 'image_filename': stats['image_filename'], 'buchos_recebidos': stats['buchos_recebidos'], 'name': stats['name'], 'buchos_dados': stats['buchos_dados']} for pid, stats in top_buchos_dados_ord]
    print(f'TOP BUCHOS DADOS --> {top_buchos_dados}')
    top_buchos_recebidos_ord = sorted(player_stats.items(), key=lambda x: x[1]['buchos_recebidos'], reverse=True)[:3]
    top_buchos_recebidos = [{'id': pid, 'image_filename': stats['image_filename'], 'buchos_recebidos': stats['buchos_recebidos'], 'name': stats['name'], 'buchos_dados': stats['buchos_dados']} for pid, stats in top_buchos_recebidos_ord]
    print(f'TOP BUCHOS RECEBIDOS --> {top_buchos_recebidos}')
    return render_template('index.html', players=players, 
    game_days=game_days, order_by=order_by, order_type=order_type, 
    top_buchos_dados=top_buchos_dados, top_buchos_recebidos=top_buchos_recebidos)

@app.route('/registrar_jogador', methods=['GET', 'POST'])
def registrar_jogador():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    form = PlayerForm()
    form.set_submit_label("Registrar")
    if form.validate_on_submit():
        player = Player(name=form.name.data, points=form.points.data,
        buchos_dados = form.buchos_dados.data, 
        buchos_recebidos = form.buchos_recebidos.data,
        frequencia_dias = form.frequencia_dias.data)
        
        cropped_image_data = request.form.get('cropped_image')
        
        if cropped_image_data:
            header, encoded = cropped_image_data.split(",", 1)
            
            decoded_data = base64.b64decode(encoded)
            
            filename = secure_filename(form.name.data + ".png")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            with open(filepath, 'wb') as f:
                f.write(decoded_data)
            
            player.image_filename = filename
        
        db.session.add(player)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('registrarjogador.html', form=form)


@app.route('/edit/<int:player_id>', methods=['GET', 'POST'])
def edit_player(player_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    player = Player.query.get_or_404(player_id)
    form = PlayerForm(obj=player)
    form.set_submit_label("Atualizar")
    if form.validate_on_submit():
        player.name = form.name.data
        player.points = form.points.data
        player.buchos_dados = form.buchos_dados.data
        player.buchos_recebidos = form.buchos_recebidos.data
        player.frequencia_dias = form.frequencia_dias.data
        
        cropped_image_data = request.form.get('cropped_image')
                
        if cropped_image_data:
            header, encoded = cropped_image_data.split(",", 1)
            
            decoded_data = base64.b64decode(encoded)
            
            filename = secure_filename(form.name.data + ".png")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            with open(filepath, 'wb') as f:
                f.write(decoded_data)
            
            player.image_filename = filename
                
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('edit_player.html', form=form, player=player)

@app.route('/delete/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    player = Player.query.get_or_404(player_id)

    game_day_players = GameDayPlayerDetails.query.filter_by(player_id=player_id).all()
    for game_day_player in game_day_players:
        db.session.delete(game_day_player)

    db.session.delete(player)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/add_player_to_game_day/<int:game_day_id>', methods=['GET', 'POST'])
def add_player_to_game_day(game_day_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    game_day = GameDay.query.get_or_404(game_day_id)
    
    players_not_in_game_day = Player.query.filter(Player.id.notin_([player.player_id for player in game_day.player_details])).all()
    
    form = GameDayForm()
    form.player_ids.choices = [(player.id, player.name) for player in players_not_in_game_day]
    form.date.data = game_day.date
    if form.validate_on_submit():
        selected_player_ids = form.player_ids.data
        
        for player_id in selected_player_ids:
            player = Player.query.get_or_404(player_id)
            player.points += 200
            player.frequencia_dias += 1
            detail = GameDayPlayerDetails.query.filter_by(game_day=game_day, player=player).first()
            if not detail:
                detail = GameDayPlayerDetails(game_day=game_day, player=player)
                db.session.add(detail)
        
        for player_id in selected_player_ids:
            player = Player.query.get_or_404(player_id)
            game_day_player_detail = GameDayPlayerDetails.query.filter_by(game_day=game_day, player=player).first()
            if game_day_player_detail:
                game_day_player_detail.buchos_given = 0
                game_day_player_detail.buchos_received = 0
        
        db.session.commit()
        return redirect(url_for('view_game_day', game_day_id=game_day_id))
    
    return render_template('add_player_to_game_day.html', form=form, game_day=game_day)


@app.route('/delete_game_day/<int:game_day_id>', methods=['POST'])
def delete_game_day(game_day_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    gameDay = GameDay.query.get_or_404(game_day_id)
    gameDayPlayer = GameDayPlayerDetails.query.filter_by(game_day=gameDay).all()
    gameDayPlayers = []
    for gdp in gameDayPlayer:
        gameDayPlayers.append(gdp.player)
        gdp.player.buchos_recebidos -= gdp.buchos_received
        gdp.player.buchos_dados -= gdp.buchos_given
        gdp.player.frequencia_dias -= 1
        gdp.player.points -= 100
        gdp.player.points += gdp.buchos_received * 150
        gdp.player.points -= gdp.buchos_given * 10

    all_players = Player.query.all() 
    for player in all_players:
        if player not in gameDayPlayers:
            player.points += 100
            db.session.commit()

    db.session.delete(gameDay)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/tabela_buchos')
def tabela_buchos():
    players = Player.query.all()
    game_days = GameDay.query.all()
    
    # Adicionando a data formatada a cada game_day
    for game_day in game_days:
        game_day.formatted_date = game_day.date.strftime('%d/%m/%y')
    
    table_data = []
    for player in players:
        player_data = {"name": player.name}
        total_bd = 0  
        total_br = 0  
        
        for game_day in game_days:
            detail = GameDayPlayerDetails.query.filter_by(game_day_id=game_day.id, player_id=player.id).first()
            if detail:
                player_data[f"{game_day.date}_dados"] = detail.buchos_given
                player_data[f"{game_day.date}_recebidos"] = detail.buchos_received
                total_bd += detail.buchos_given  
                total_br += detail.buchos_received  
            else:
                player_data[f"{game_day.date}_dados"] = 0
                player_data[f"{game_day.date}_recebidos"] = 0
        
        player_data["total_bd"] = total_bd
        player_data["total_br"] = total_br  
        player_data["total_points"] = player.points
        table_data.append(player_data)
        
    return render_template('tabela_buchos.html', table_data=table_data, game_days=game_days)


@app.route('/delete_game_day_player/<int:game_day_id>/<int:game_day_player_id>', methods=['POST'])
def delete_game_day_player(game_day_id, game_day_player_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    gameDayPlayer = GameDayPlayerDetails.query.get_or_404(game_day_player_id)
    player = Player.query.get_or_404(gameDayPlayer.player.id)
    player.buchos_recebidos -= gameDayPlayer.buchos_received
    player.buchos_dados -= gameDayPlayer.buchos_given
    player.frequencia_dias -= 1
    player.points -= 200
    player.points += gameDayPlayer.buchos_received * 150
    player.points -= gameDayPlayer.buchos_given * 100

    db.session.delete(gameDayPlayer)
    db.session.commit()
    return redirect(url_for('view_game_day', game_day_id=game_day_id))

if __name__ == '__main__':
    with app.app_context():
        #schedule_reset()
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))