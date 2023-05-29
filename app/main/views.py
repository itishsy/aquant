from app import get_logger, get_config
import math
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import utils
from app.models import Notify, Signal, Ticket
from app.main.forms import NotifyForm, SignalForm, TicketForm
from . import main
from storage.db import count_signals, count_tickets, get_signal, update_signal_watch, save_ticket_by_signal
from enums.entity import Entity
from conf.config import Config

logger = get_logger(__name__)
cfg = get_config()


# 通用列表查询
def common_list(DynamicModel, view):
    # 接收参数
    action = request.args.get('action')
    id = request.args.get('id')
    page = int(request.args.get('page')) if request.args.get('page') else 1
    length = int(request.args.get('length')) if request.args.get('length') else cfg.ITEMS_PER_PAGE

    # 删除操作
    if action == 'del' and id:
        try:
            DynamicModel.get(DynamicModel.id == id).delete_instance()
            flash('删除成功')
        except:
            flash('删除失败')

    # 查询列表
    query = DynamicModel.select()
    total_count = query.count()

    # 处理分页
    if page: query = query.paginate(page, length)

    dict = {'content': utils.query_to_list(query), 'total_count': total_count,
            'total_page': math.ceil(total_count / length), 'page': page, 'length': length}
    return render_template(view, form=dict, current_user=current_user)


# 通用单模型查询&新增&修改
def common_edit(DynamicModel, form, view):
    id = request.args.get('id', '')
    if id:
        # 查询
        model = DynamicModel.get(DynamicModel.id == id)
        if request.method == 'GET':
            utils.model_to_form(model, form)
        # 修改
        if request.method == 'POST':
            if form.validate_on_submit():
                utils.form_to_model(form, model)
                model.save()
                flash('修改成功')
            else:
                utils.flash_errors(form)
    else:
        # 新增
        if form.validate_on_submit():
            model = DynamicModel()
            utils.form_to_model(form, model)
            model.save()
            flash('保存成功')
        else:
            utils.flash_errors(form)
    return render_template(view, form=form, current_user=current_user)


# 根目录跳转
@main.route('/', methods=['GET'])
@login_required
def root():
    return redirect(url_for('main.index'))


# 首页
@main.route('/index', methods=['GET'])
@login_required
def index():
    return render_template('index.html', current_user=current_user)


# 根目录跳转
@main.route('/api/stats/summary', methods=['GET'])
@login_required
def api():
    s_signal = count_signals()
    t_signal = count_signals(today=True)
    data = {'count01': s_signal, 'count02': t_signal, 'count03': count_tickets(), 'count04': 46}
    return jsonify(data)


# 根目录跳转
@main.route('/api/save/ticket', methods=['POST'])
@login_required
def save_ticket():
    id = request.args.get('id')
    status = request.args.get('status')
    sig = get_signal(id)
    if sig is None:
        ok = 0
    else:
        print('========', id, status, sig)
        update_signal_watch(id, status)
        ok = save_ticket_by_signal(sig, status)
    data = {'ok': ok}
    return jsonify(data)


# 通知方式查询
@main.route('/notifylist', methods=['GET', 'POST'])
@login_required
def notifylist():
    return common_list(Notify, 'notifylist.html')


# 通知方式配置
@main.route('/notifyedit', methods=['GET', 'POST'])
@login_required
def notifyedit():
    return common_edit(Notify, NotifyForm(), 'notifyedit.html')


@main.route('/signallist', methods=['GET', 'POST'])
@login_required
def signallist():
    return common_list(Signal, 'signallist.html')


@main.route('/signaledit', methods=['GET', 'POST'])
@login_required
def signaledit():
    return common_edit(Signal, SignalForm(), 'signaledit.html')


@main.route('/ticketlist', methods=['GET', 'POST'])
@login_required
def ticketlist():
    return common_list(Ticket, 'ticketlist.html')


@main.route('/ticketedit', methods=['GET', 'POST'])
@login_required
def ticketedit():
    return common_edit(Ticket, TicketForm(), 'ticketedit.html')
