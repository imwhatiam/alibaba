# coding=utf-8
# !/usr/bin/env python

import json
import pymssql
import ConfigParser
from seahub.share.settings import PINGAN_DLP_DATABASE_CONF, \
        PINGAN_DLP_DB_CONNECT_TIMEOUT, PINGAN_DLP_DB_LOGIN_CONNECT_TIMEOUT


class MSSQL:
    def __init__(self):
        cf = ConfigParser.ConfigParser()
        cf.read(PINGAN_DLP_DATABASE_CONF)
        self.host = cf.get("DB", "host")
        self.user = cf.get("DB", "user")
        self.pwd = cf.get("DB", "pwd")
        self.db = cf.get("DB", "db")

    def __GetConnect(self):
        """
        get connetion info
        response: conn.cursor()
        """
        # if not self.db:
        #    raise(NameError,"no db conf file found")

        self.conn = pymssql.connect(host=self.host, user=self.user, password=self.pwd,
                database=self.db, charset="utf8",
                timeout=PINGAN_DLP_DB_CONNECT_TIMEOUT,
                login_timeout=PINGAN_DLP_DB_LOGIN_CONNECT_TIMEOUT)
        cur = self.conn.cursor()

        if not cur:
            raise (NameError, "fail connecting to DB")
        else:
            return cur

    ##verify DB connection
    def VerifyConnection(self):
        try:
            if self.host == '':
                return False
            pymssql.connect(host=self.host, user=self.user, password=self.pwd, database=self.db,
                    timeout=PINGAN_DLP_DB_CONNECT_TIMEOUT, charset="utf8",
                    login_timeout=PINGAN_DLP_DB_LOGIN_CONNECT_TIMEOUT)
            return True
        except:
            return False

    def ExecQuery(self, sql):
        """
        execute query
        get a list including tuple, elements of list are row of record, elements of tuple is fields

        demo
                ms = MSSQL(host="localhost",user="sa",pwd="123456",db="PythonWeiboStatistics")
                resList = ms.ExecQuery("SELECT id,NickName FROM WeiBoUser")
                for (id,NickName) in resList:
                    print str(id),NickName
        """
        cur = self.__GetConnect()
        cur.execute(sql)
        resList = cur.fetchall()
        self.conn.close()
        return resList

    def ExecNonQuery(self, sql):
        """
        execute no query
        demo
            cur = self.__GetConnect()
            cur.execute(sql)
            self.conn.commit()
            self.conn.close()
        """
        cur = self.__GetConnect()
        cur.execute(sql)
        self.conn.commit()
        self.conn.close()

    def ExecStoreProduce(self, sql):
        """
        execute query
        get a list including tuple, elements of list are row of record, elements of tuple is fields

        demo:
                ms = MSSQL(host="localhost",user="sa",pwd="123456",db="PythonWeiboStatistics")
                resList = ms.ExecQuery("SELECT id,NickName FROM WeiBoUser")
                for (id,NickName) in resList:
                    print str(id),NickName
        """
        cur = self.__GetConnect()
        cur.execute(sql)
        resList = cur.fetchall()
        self.conn.commit()
        self.conn.close()
        return resList

    def CheckDLP(self, file_path, filesize, mtime):
        """
        according filepath check DLP scan result
        """
        filepath = file_path.replace('/', '\\')
        filepath = self.sqlExcape(filepath)
        cur = self.__GetConnect()
        filepath1 = filepath.replace('\'', '\'\'')
        print('\ncheck dlp for: ' + filepath1)

        result = 0, 'not scan'

        sql1 = "select count(*) as cnt from [wbsn-data-security]..[PA_DSCVR_FILES] where FILEPATH like N'%" + filepath1 + "' and FILE_SIZE=%d and [POLICY_CATEGORIES]= 'permit'" % filesize
        cur.execute(sql1.encode('utf-8'))
        resList1 = cur.fetchall()
        if int(resList1[0][0]) > 0:
            result = 1, 'ok'

        sql2 = "select count(*) as cnt from [wbsn-data-security]..[PA_DSCVR_FILES] where FILEPATH like N'%" + filepath1 + "' and charindex('block',[POLICY_CATEGORIES])>0 and FILE_SIZE=%d" % filesize
        cur.execute(sql2.encode('utf-8'))
        resList2 = cur.fetchall()
        if int(resList2[0][0]) > 0:
            result = 2, 'block'

        sql3 = "select count(*) as cnt from [wbsn-data-security]..[PA_DSCVR_FILES] where FILEPATH like N'%" + filepath1 + "' and charindex('block_high_risk',[POLICY_CATEGORIES])>0 and FILE_SIZE=%d" % filesize
        cur.execute(sql3.encode('utf-8'))
        resList3 = cur.fetchall()
        if int(resList3[0][0]) > 0:
            sql4 = "SELECT [ID],[FILENAME],[POLICY_CATEGORIES],[FILE_SIZE],[TOTAL_MATCHES],[INSERT_DATE],[BREACH_CONTENT] FROM [wbsn-data-security].[dbo].[PA_DSCVR_FILES] where FILEPATH like N'%" + filepath1 + "' and charindex('block_high_risk',[POLICY_CATEGORIES])>0 and FILE_SIZE=%d" % filesize
            cur.execute(sql4.encode('utf-8'))
            resList4 = cur.fetchone()

            dlp_msg = {}
            dlp_msg['file_name'] = resList4[1]
            dlp_msg['policy_categories'] = resList4[2]
            dlp_msg['total_matches'] = resList4[4]
            dlp_msg['breach_content'] = resList4[6]

            result = 3, json.dumps(dlp_msg)

        self.conn.commit()
        self.conn.close()
        print(str(result))
        return result

    # Created by WANGZEXIN289
    # 功能：对DLP的查询SQL中包含的特殊字符进行转义
    def sqlExcape(self, partial_path):
        specialChar = set(['[', '%', '_', '^'])
        for char in specialChar:
            partial_path = partial_path.replace(char, '[%s]' % char)
        return partial_path
