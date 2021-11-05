import json
import logging
import traceback

import email_utility
import pandas
import pandas_utility
from email_operator import send_email
from Project_declaration_robot import ProjectDeclarationRobot
from udp.udp import UDPManager

udp_receive = UDPManager("localhost", 12080)
udp_receive.socket_client.bind(("localhost", udp_receive.port))

udp_send = UDPManager("localhost", 13080)
udp_send.socket_client.connect(("localhost", udp_send.port))

output_path = ""


class EmailException(Exception):
    """
    邮件异常统称
    """

    def __init__(self, msg):
        super(EmailException, self).__init__(msg)
        self.msg = msg

    def __str__(self):
        return self.msg


def robot_run(thread_num=1):
    # 接收开始信息
    print("\n等待启动\n")
    info = udp_receive.data_receive()
    info = json.loads(info)

    if info["type"] == "开始":
        finance_file_path = info["project_finance_file"]
        personal_file_path = info["person_salary_file"]
        output_path = info["output_path"]

        print("项目财务凭证表路径: " + finance_file_path)
        print("个人薪资明细表路径: " + personal_file_path)
        print("输出文件路径: " + output_path)
        print("邮箱账号: " + info["email_account"])
        print("邮箱主题: " + info["email_theme"])

        # 收到前端传来的路径, 运行机器人
        print("\n开始机器人")
        robot = ProjectDeclarationRobot(
            finance_file_path=finance_file_path,
            personal_file_path=personal_file_path,
            output_file_name="项目人员工资表明细",  # 后缀写入在run()里面
            output_path=output_path,
        )

        # 根据参数thread_num 决定单线程或者多线程
        if thread_num < 1:
            raise Exception("robot_run(thread_num): thread_num线程数量必须大于或等于1")
        elif thread_num == 1:
            robot.run()
        else:
            robot.run_parallel(thread_num)  # 多线程（线程池）

        send_complete_msg(info)


def send_complete_msg(info):
    # 发完成邮件
    try:
        if len(info["email_account"]) != 0:
            print("发送邮件中")
            # 存在收邮件人, 需要发送邮件
            email_list = info["email_account"].split(";")
            email_theme = info["email_theme"]
            send_email(email_list, "立项通知书RPA机器人已完成任务", email_theme)

    except Exception as e:
        raise EmailException(str(e))

    # 发生完成信息给前端，并附带输出文件路径
    print()
    email_utility.send_complete_message(
        udp=udp_send, message="", path=info["output_path"]
    )

    print("完成")


if __name__ == "__main__":
    pandas.read_excel("C:\\Users\\bowu10\\Desktop\\拉沙表\\磨渔场码头8.23新河口拉运统计表(1).xls")
    # os.system('start front_end\\Audit-rpa.exe')

    while True:
        try:
            pandas_utility.config_log()
            robot_run()

        except EmailException as e:
            exception_info = traceback.format_exc()
            logging.getLogger().debug(exception_info)

            # 捕获邮件功能异常, 并发送给前端
            email_utility.send_warning_message(
                udp=udp_send,
                message='邮件通知功能异常！"立项通知书"文件已输出至: ',
                path=output_path,
            )
            # 打印出来
            print('邮件通知功能异常！"立项通知书"文件已输出至: ' + output_path)

        except Exception as e:
            exception_info = traceback.format_exc()
            logging.getLogger().debug(exception_info)

            print(exception_info)
            # 捕获邮件异常之外的所有的exception, 并发送给前端
            email_utility.send_error_message(udp_send, str(e))
            # 打印出来
            print(str(e))
