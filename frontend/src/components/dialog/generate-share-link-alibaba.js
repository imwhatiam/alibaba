import React, { Fragment } from 'react';
import PropTypes from 'prop-types';
import moment from 'moment';
import copy from 'copy-to-clipboard';
import { Row, Col, Button, Form, FormGroup, Label, Input, InputGroup, InputGroupAddon, Alert } from 'reactstrap';
import { gettext, shareLinkExpireDaysMin, shareLinkExpireDaysMax, shareLinkExpireDaysDefault, shareLinkPasswordMinLength } from '../../utils/constants';
import { seafileAPI } from '../../utils/seafile-api';
import { Utils } from '../../utils/utils';
import SharedLinkInfo from '../../models/share-link';
import toaster from '../toast';
import Loading from '../loading';
import ShareLinksPermissionEditorAlibaba from '../select-editor/share-links-permission-editor-alibaba';

const propTypes = {
  itemPath: PropTypes.string.isRequired,
  repoID: PropTypes.string.isRequired,
  closeShareDialog: PropTypes.func.isRequired,
};

class GenerateShareLinkAlibaba extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      isValidate: false,
      isShowPasswordInput: false,
      isPasswordVisible: false,
      isExpireChecked: false,
      password: '',
      passwdnew: '',
      expireDays: shareLinkExpireDaysDefault,
      errorInfo: '',
      sharedLinkInfo: null,
      isNoticeMessageShow: false,
      isLoading: true,
      isShowSendLink: false,
      sendLinkEmails: '',
      sendLinkMessage: '',
      sendLinkErrorMessage: '',
      fileInfo: null,
      currentPermission: '',
    };
    this.permissions = {
      'can_edit': false, 
      'can_download': false
    };
    this.isExpireDaysNoLimit = (parseInt(shareLinkExpireDaysMin) === 0 && parseInt(shareLinkExpireDaysMax) === 0);
  }

  componentDidMount() {
    let path = this.props.itemPath; 
    let repoID = this.props.repoID;
    seafileAPI.getShareLink(repoID, path).then((res) => {
      if (res.data.length !== 0) {
        let sharedLinkInfo = new SharedLinkInfo(res.data[0]);
        this.setState({
          isLoading: false,
          currentPermission: sharedLinkInfo.permissions.can_edit ? 'editOnCloud' : 'previewOnCloud',
          sharedLinkInfo: sharedLinkInfo
        });
      } else {
        this.setState({isLoading: false});
      }
    });
    this.getFileInfo();
  }

  getFileInfo = () => {
    let path = this.props.itemPath;
    let repoID = this.props.repoID;
    seafileAPI.getFileInfo(repoID, path).then((res) => {
      if (res.data){
        this.setState({fileInfo: res.data});
      }
    });
  }

  onPasswordInputChecked = () => {
    this.setState({
      isShowPasswordInput: !this.state.isShowPasswordInput,
      password: '',
      passwdnew: '',
      errorInfo: ''
    });
  }

  togglePasswordVisible = () => {
    this.setState({
      isPasswordVisible: !this.state.isPasswordVisible
    });
  }

  generatePassword = () => {
    let val = Utils.generatePassword(shareLinkPasswordMinLength);
    this.setState({
      password: val,
      passwdnew: val
    });
  }

  inputPassword = (e) => {
    let passwd = e.target.value.trim();
    this.setState({password: passwd});
  }

  inputPasswordNew = (e) => {
    let passwd = e.target.value.trim();
    this.setState({passwdnew: passwd});
  }

  setPermission = (permission) => {
    if (permission == 'previewOnCloud') {
      this.permissions = {
        'can_edit': false,
        'can_download': false,
      };
      this.setState({currentPermission: 'previewOnCloud'});
    } else if (permission == 'editOnCloud') {
      this.permissions = {
        'can_edit': true,
        'can_download': false,
      };
      this.setState({currentPermission: 'editOnCloud'});
    } else {
      this.permissions = {
        'can_edit': false,
        'can_download': false
      };     
    }
  }

  generateShareLink = () => {
    let isValid = this.validateParamsInput();
    if (isValid) {
      this.setState({errorInfo: ''});
      let { itemPath, repoID } = this.props;
      let { password, expireDays } = this.state;
      let permissions = this.permissions;
      permissions = JSON.stringify(permissions);
      seafileAPI.createShareLink(repoID, itemPath, password, expireDays, permissions).then((res) => {
        let sharedLinkInfo = new SharedLinkInfo(res.data);
        this.setState({sharedLinkInfo: sharedLinkInfo});
        this.setState({
          currentPermission: sharedLinkInfo.permissions.can_edit ? 'editOnCloud' : 'previewOnCloud',
        });
      });
    }
  }

  onCopySharedLink = () => {
    let sharedLink = this.state.sharedLinkInfo.link;
    copy(sharedLink);
    toaster.success(gettext('Share link is copied to the clipboard.'));
    this.props.closeShareDialog();
  }
  
  onCopyDownloadLink = () => {
    let downloadLink = this.state.sharedLinkInfo.link + '?dl';
    copy(downloadLink);
    toaster.success(gettext('Direct download link is copied to the clipboard.'));
    this.props.closeShareDialog();
  }

  deleteShareLink = () => {
    let sharedLinkInfo = this.state.sharedLinkInfo;
    seafileAPI.deleteShareLink(sharedLinkInfo.token).then(() => {
      this.setState({
        password: '',
        passwordnew: '',
        isShowPasswordInput: false,
        expireDays: shareLinkExpireDaysDefault,
        isExpireChecked: false,
        errorInfo: '',
        sharedLinkInfo: null,
        isNoticeMessageShow: false,
      });
      this.permissions = {
        'can_edit': false,
        'can_download': false
      };
    });
  }

  onExpireChecked = (e) => {
    this.setState({isExpireChecked: e.target.checked});
  }

  onExpireDaysChanged = (e) => {
    let day = e.target.value.trim();
    this.setState({expireDays: day});
  }

  validateParamsInput = () => {
    let { isShowPasswordInput , password, passwdnew, isExpireChecked, expireDays } = this.state;
    // validate password
    if (isShowPasswordInput) {
      if (password.length === 0) {
        this.setState({errorInfo: 'Please enter password'});
        return false;
      }
      if (password.length < shareLinkPasswordMinLength) {
        this.setState({errorInfo: 'Password is too short'});
        return false;
      }
      if (password !== passwdnew) {
        this.setState({errorInfo: 'Passwords don\'t match'});
        return false;
      }
    }

    // validate days
    // no limit
    let reg = /^\d+$/;
    if (this.isExpireDaysNoLimit) {
      if (isExpireChecked) {
        if (!expireDays) {
          this.setState({errorInfo: 'Please enter days'});
          return false;
        }
        if (!reg.test(expireDays)) {
          this.setState({errorInfo: 'Please enter a non-negative integer'});
          return false;
        }
        this.setState({expireDays: parseInt(expireDays)});
      }
    } else {
      if (!expireDays) {
        this.setState({errorInfo: 'Please enter days'});
        return false;
      }
      if (!reg.test(expireDays)) {
        this.setState({errorInfo: 'Please enter a non-negative integer'});
        return false;
      }

      expireDays = parseInt(expireDays);
      let minDays = parseInt(shareLinkExpireDaysMin);
      let maxDays = parseInt(shareLinkExpireDaysMax);

      if (minDays !== 0 && maxDays !== maxDays) {
        if (expireDays < minDays) {
          this.setState({errorInfo: 'Please enter valid days'});
          return false;
        }
      }
      
      if (minDays === 0 && maxDays !== 0 ) {
        if (expireDays > maxDays) {
          this.setState({errorInfo: 'Please enter valid days'});
          return false;
        }
      }
      
      if (minDays !== 0 && maxDays !== 0) {
        if (expireDays < minDays || expireDays > maxDays) {
          this.setState({errorInfo: 'Please enter valid days'});
          return false;
        }
      }
      this.setState({expireDays: expireDays});
    }

    return true;
  }

  changePerm = (changed_to_permissions) => {
    let permissions = this.permissions;

    if (changed_to_permissions === 'previewOnCloud'){
      permissions.can_edit = false;
    } else if (changed_to_permissions === 'editOnCloud'){
      permissions.can_edit = true;
    }
    seafileAPI.updateShareLink(this.state.sharedLinkInfo.token, JSON.stringify(permissions)).then(() => {
      this.setState({
        currentPermission: changed_to_permissions,
      });
      toaster.success(gettext('Successfully modified permission'));
    }).catch((error) => {
      // TODO: show feedback msg
    });
  }

  onNoticeMessageToggle = () => {
    this.setState({isNoticeMessageShow: !this.state.isNoticeMessageShow});
  }

  onSendLinkEmailsChange = (event) => {
    if (this.state.sendLinkErrorMessage) this.setState({ sendLinkErrorMessage: '' });
    this.setState({sendLinkEmails: event.target.value});
  }

  onSendLinkMessageChange = (event) => {
    if (this.state.sendLinkErrorMessage) this.setState({ sendLinkErrorMessage: '' });
    this.setState({sendLinkMessage: event.target.value});
  }

  toggleSendLink = () => {
    this.setState({ isShowSendLink: !this.state.isShowSendLink });
  }

  sendShareLink = () => {
    if (!this.state.sendLinkEmails) return;
    const token = this.state.sharedLinkInfo.token;
    const emails = this.state.sendLinkEmails.replace(/\s*/g,'');
    const message = this.state.sendLinkMessage.trim();
    this.setState({ isLoading: true });
    seafileAPI.sendShareLink(token, emails, message).then((res) => {
      this.props.closeShareDialog();
      if (res.data.failed.length > 0) {
        res.data.failed.map(failed => {
          toaster.warning(gettext('Failed sent link to') + ' ' + failed.email + ', ' + failed.error_msg);
        });
      }
      if (res.data.success.length > 0) {
        let users = res.data.success.join(',');
        toaster.success(gettext('Successfully sent link to') + ' ' + users);
      }
    }).catch((error) => {
      if (error.response) {
        this.setState({
          sendLinkErrorMessage: error.response.data.error_msg,
          isLoading: false,
        });
      }
    });
  }

  render() {


    if (this.state.isLoading) {
      return <Loading />;
    }
    let isZHCN = window.app.config.lang === 'zh-cn';
    let passwordLengthTip = gettext('(at least {passwordLength} characters)');
    passwordLengthTip = passwordLengthTip.replace('{passwordLength}', shareLinkPasswordMinLength);

    let canEditByFileInfoOrUmind = false;
    let file_ext = '';
    if (this.props.itemPath.lastIndexOf('.') != -1) {
      file_ext = this.props.itemPath.substr(this.props.itemPath.lastIndexOf('.') + 1).toLowerCase();
    }
    if ((this.state.fileInfo && this.state.fileInfo.can_edit) || file_ext == 'umind'){
      canEditByFileInfoOrUmind = true;
    }

    if (this.state.sharedLinkInfo) {
      let sharedLinkInfo = this.state.sharedLinkInfo;
      return (
        <div>
          <p>{isZHCN ? '查看链接： 阿里巴巴经济体内，获取该链接的任何人可以查看该文件' : 'View Link: Within Alibaba Group, anyone who gets the link can VIEW the file'}</p>
          <Form className="mb-4">
            <FormGroup className="mb-0">
              <dt className="text-secondary font-weight-normal">{gettext('Link:')}</dt>
              <dd className="d-flex">
                <span>{sharedLinkInfo.link}</span>{' '}
                {sharedLinkInfo.is_expired ?
                  <span className="err-message">({gettext('Expired')})</span> :
                  <span className="far fa-copy action-icon" onClick={this.onCopySharedLink}></span>
                }
              </dd>
            </FormGroup>
            {sharedLinkInfo.password && (
              <FormGroup className="mb-0">
                <dt className="text-secondary font-weight-normal">{isZHCN ? '密码：' : 'Password: '}</dt>
                <dd className="d-flex">
                  <span>{sharedLinkInfo.password}</span>{' '}
                </dd>
              </FormGroup>
            )}
            {sharedLinkInfo.expire_date && (
              <FormGroup className="mb-0">
                <dt className="text-secondary font-weight-normal">{gettext('Expiration Date:')}</dt>
                <dd>{moment(sharedLinkInfo.expire_date).format('YYYY-MM-DD hh:mm:ss')}</dd>
              </FormGroup>
            )}
            {canEditByFileInfoOrUmind &&
            <Row>
              <Col md={6}>
                <ShareLinksPermissionEditorAlibaba
                  currentPermission={this.state.currentPermission}
                  permissionOptions={['previewOnCloud', 'editOnCloud']}
                  onPermissionChanged={this.changePerm}
                />
              </Col>
            </Row>}
          </Form>
          {/* {(!this.state.isShowSendLink && !this.state.isNoticeMessageShow) &&
            <Button onClick={this.toggleSendLink} className='mr-2'>{gettext('Send')}</Button>
          } */}
          {this.state.isShowSendLink &&
            <Fragment>
              <Form>
                <FormGroup>
                  <Label htmlFor="sendLinkEmails" className="text-secondary font-weight-normal">{gettext('Send to')}{':'}</Label>
                  <Input 
                    id="sendLinkEmails"
                    className="w-75"
                    value={this.state.sendLinkEmails}
                    onChange={this.onSendLinkEmailsChange}
                    placeholder={gettext('Emails, separated by \',\'')}
                  />
                </FormGroup>
                <FormGroup>
                  <Label htmlFor="sendLinkMessage" className="text-secondary font-weight-normal">{gettext('Message (optional):')}</Label><br/>
                  <textarea
                    className="w-75"
                    id="sendLinkMessage"
                    value={this.state.sendLinkMessage}
                    onChange={this.onSendLinkMessageChange}
                  ></textarea>
                </FormGroup>
              </Form>
              {this.state.sendLinkErrorMessage && <p className="error">{this.state.sendLinkErrorMessage}</p>}
              <Button color="primary" onClick={this.sendShareLink}>{gettext('Send')}</Button>{' '}
              <Button color="secondary" onClick={this.toggleSendLink}>{gettext('Cancel')}</Button>{' '}
            </Fragment>
          }
          {(!this.state.isShowSendLink && !this.state.isNoticeMessageShow) &&
            <Button onClick={this.onNoticeMessageToggle}>{gettext('Delete')}</Button>
          }
          {this.state.isNoticeMessageShow &&
            <div className="alert alert-warning">
              <h4 className="alert-heading">{gettext('Are you sure you want to delete the share link?')}</h4>
              <p className="mb-4">{gettext('If the share link is deleted, no one will be able to access it any more.')}</p>
              <button className="btn btn-primary" onClick={this.deleteShareLink}>{gettext('Delete')}</button>{' '}
              <button className="btn btn-secondary" onClick={this.onNoticeMessageToggle}>{gettext('Cancel')}</button>
            </div>
          }
        </div>
      );
    } else if(this.state.fileInfo) {
      let fileInfo = this.state.fileInfo;

      return (
      <div>
        {(!canEditByFileInfoOrUmind && !fileInfo.can_preview) &&
          <Form className="generate-share-link">
            <span>{isZHCN ? '该文件格式不支持云端预览和云端编辑' : 'Neither view link nor edit link is applicable to this file format'}</span>
          </Form>
        }
        {(fileInfo.can_edit || fileInfo.can_preview) &&
        <Form className="generate-share-link">
          <FormGroup check>
            <Label check>
              <Input type="checkbox" onChange={this.onPasswordInputChecked}/>{'  '}{gettext('Add password protection')} 
            </Label>
          </FormGroup>
          {this.state.isShowPasswordInput &&
            <FormGroup className="link-operation-content" check>
              <Label className="font-weight-bold">{gettext('Password')}</Label>{' '}<span className="tip">{passwordLengthTip}</span>
              <InputGroup className="passwd">
                <Input type={this.state.isPasswordVisible ? 'text' : 'password'} value={this.state.password || ''} onChange={this.inputPassword}/>
                <InputGroupAddon addonType="append">
                  <Button onClick={this.togglePasswordVisible}><i className={`link-operation-icon fas ${this.state.isPasswordVisible ? 'fa-eye': 'fa-eye-slash'}`}></i></Button>
                  <Button onClick={this.generatePassword}><i className="link-operation-icon fas fa-magic"></i></Button>
                </InputGroupAddon>
              </InputGroup>
              <Label className="font-weight-bold">{gettext('Password again')}</Label>
              <Input className="passwd" type={this.state.isPasswordVisible ? 'text' : 'password'} value={this.state.passwdnew || ''} onChange={this.inputPasswordNew} />
            </FormGroup>
          }
          {this.isExpireDaysNoLimit && (
            <Fragment>
              <FormGroup check>
                <Label check>
                  <Input className="expire-checkbox" type="checkbox" onChange={this.onExpireChecked}/>{'  '}{gettext('Add auto expiration')}
                </Label>
              </FormGroup>
              {this.state.isExpireChecked && 
                <FormGroup check>
                  <Label check>
                    <Input className="expire-input expire-input-border" type="text" value={this.state.expireDays} onChange={this.onExpireDaysChanged} readOnly={!this.state.isExpireChecked}/><span className="expir-span">{gettext('days')}</span>
                  </Label>
                </FormGroup>
              }
            </Fragment>
          )}
          {!this.isExpireDaysNoLimit && (
            <Fragment>
              <FormGroup check>
                <Label check>
                  <Input className="expire-checkbox" type="checkbox" onChange={this.onExpireChecked} checked readOnly disabled/>{'  '}{gettext('Add auto expiration')}
                </Label>
              </FormGroup>
              <FormGroup check>
                <Label check>
                  <Input className="expire-input expire-input-border" type="text" value={this.state.expireDays} onChange={this.onExpireDaysChanged} /><span className="expir-span">{gettext('days')}</span>
                  {(parseInt(shareLinkExpireDaysMin) !== 0 && parseInt(shareLinkExpireDaysMax) !== 0) && (
                    <span className="d-inline-block ml-7">({shareLinkExpireDaysMin} - {shareLinkExpireDaysMax}{' '}{gettext('days')})</span>
                  )}
                  {(parseInt(shareLinkExpireDaysMin) !== 0 && parseInt(shareLinkExpireDaysMax) === 0) && (
                    <span className="d-inline-block ml-7">({gettext('Greater than or equal to')} {shareLinkExpireDaysMin}{' '}{gettext('days')})</span>
                  )}
                  {(parseInt(shareLinkExpireDaysMin) === 0 && parseInt(shareLinkExpireDaysMax) !== 0) && (
                    <span className="d-inline-block ml-7">({gettext('Less than or equal to')} {shareLinkExpireDaysMax}{' '}{gettext('days')})</span>
                  )}
                </Label>
              </FormGroup>
            </Fragment>
          )}
          <FormGroup check>
            <Label check>
              <span>{'  '}{isZHCN ? '读写权限控制' : 'Permission control'}</span>
            </Label>
          </FormGroup>
          {fileInfo.can_preview &&
          <FormGroup check className="permission">
            <Label check>
              <Input type="radio" name="radio1" defaultChecked={true} onChange={() => this.setPermission('previewOnCloud')}/>{'  '}{isZHCN ? '仅云端只读': 'View-on-Cloud'}
            </Label>
          </FormGroup>
          }
          {canEditByFileInfoOrUmind &&
          <FormGroup check className="permission">
            <Label>
              <Input type="radio" name="radio1" onChange={() => this.setPermission('editOnCloud')} />{'  '}{isZHCN ? '仅云端读写' : 'Edit-on-Cloud'}
            </Label>
          </FormGroup>
          }
          {this.state.errorInfo && <Alert color="danger" className="mt-2">{gettext(this.state.errorInfo)}</Alert>}
          <Button onClick={this.generateShareLink}>{gettext('Generate')}</Button>
        </Form>
       }
      </div>
      );
    }else{
      return (
        <Button className={'btn-loading'}></Button>
      );
    }
  }
}

GenerateShareLinkAlibaba.propTypes = propTypes;

export default GenerateShareLinkAlibaba;
