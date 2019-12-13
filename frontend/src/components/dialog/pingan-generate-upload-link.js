import React, { Fragment } from 'react';
import PropTypes from 'prop-types';
import copy from 'copy-to-clipboard';
import { Button, Form, FormGroup, Label, Input, InputGroup, InputGroupAddon, Alert } from 'reactstrap';
import { gettext, shareLinkPasswordMinLength } from '../../utils/constants';
import { seafileAPI } from '../../utils/seafile-api';
import { Utils } from '../../utils/utils';
import UploadLink from '../../models/upload-link';
import toaster from '../toast';
import SessionExpiredTip from '../session-expired-tip';

const propTypes = {
  itemPath: PropTypes.string.isRequired,
  repoID: PropTypes.string.isRequired,
  closeShareDialog: PropTypes.func.isRequired,
};

class GenerateUploadLinkPingan extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      showPasswordInput: true,
      passwordVisible: false,
      password: '',
      passwdnew: '',
      sharedUploadInfo: null,
    };
  }

  componentDidMount() {
    this.getUploadLink();
  }

  getUploadLink = () => {
    let path = this.props.itemPath;
    let repoID = this.props.repoID; 
    seafileAPI.getUploadLinks(repoID, path).then((res) => {
      if (res.data.length !== 0) {
        let sharedUploadInfo = new UploadLink(res.data[0]);
        this.setState({sharedUploadInfo: sharedUploadInfo});
      }
    }).catch((err) => {
      if (err.response.status === 403) {
        toaster.danger(
          <SessionExpiredTip />,
          {id: 'session_expired', duration: 3600}
        );
        this.props.closeShareDialog();
      }
    });
  }

  addPassword = () => {
    this.setState({
      showPasswordInput: !this.state.showPasswordInput,
      password: '',
      passwdnew: '',
      errorInfo: ''
    });
  }

  togglePasswordVisible = () => {
    this.setState({
      passwordVisible: !this.state.passwordVisible
    });
  }

  generatePassword = () => {
    let val = Utils.generatePassword(shareLinkPasswordMinLength);
    this.setState({
      password: val,
      passwordnew: val
    });
  }

  inputPassword = (e) => {
    this.setState({
      password: e.target.value
    });
  }

  inputPasswordNew = (e) => {
    this.setState({
      passwordnew: e.target.value
    });
  }

  generateUploadLink = () => {
    let path = this.props.itemPath;
    let repoID = this.props.repoID; 

    if (this.state.showPasswordInput && (this.state.password == '')) {
      this.setState({
        errorInfo: gettext('Please enter password')
      });
    }
    else if (this.state.showPasswordInput && (this.state.showPasswordInput && this.state.password.length < shareLinkPasswordMinLength)) {
      this.setState({
        errorInfo: gettext('Password is too short')
      });
    }
    else if (this.state.showPasswordInput && (this.state.password !== this.state.passwordnew)) {
      this.setState({
        errorInfo: gettext('Passwords don\'t match')
      });
    } else {
      seafileAPI.createUploadLink(repoID, path, this.state.password).then((res) => {
        let sharedUploadInfo = new UploadLink(res.data);
        this.setState({sharedUploadInfo: sharedUploadInfo}); 
      });
    }
  }

  onCopyUploadLink = () => {
    let uploadLink = this.state.sharedUploadInfo.link;
    copy(uploadLink);
    toaster.success(gettext('Upload link is copied to the clipboard.'));
    this.props.closeShareDialog();
  }

  deleteUploadLink = () => {
    let sharedUploadInfo = this.state.sharedUploadInfo;
    seafileAPI.deleteUploadLink(sharedUploadInfo.token).then(() => {
      this.setState({
        showPasswordInput: true,
        password: '',
        passwordnew: '',
        sharedUploadInfo: null,
      });
    });
  }

  render() {

    let passwordLengthTip = gettext('(at least {passwordLength} characters)');
    passwordLengthTip = passwordLengthTip.replace('{passwordLength}', shareLinkPasswordMinLength);
    if (this.state.sharedUploadInfo) {
      let sharedUploadInfo = this.state.sharedUploadInfo;
      return (
        <div>
          <Label className="text font-weight-normal">{'你可以共享生成好的链接给别人，他们就能通过这个链接上传文件到这个文件夹。'}</Label>
          <Form className="mb-4">
            <FormGroup>
              <dt className="text-secondary font-weight-normal">{gettext('Upload Link:')}</dt>
              <dd className="d-flex">
                <span>{sharedUploadInfo.link}</span>
                <span className="far fa-copy action-icon" onClick={this.onCopyUploadLink}></span>
              </dd>
            </FormGroup>
            {sharedUploadInfo.password && (
                <FormGroup className="mb-0">
                  <dt className="text-secondary font-weight-normal">{'密码：'}</dt>
                  <dd className="d-flex">
                    <span>{sharedUploadInfo.password}</span>{' '}
                  </dd>
                </FormGroup>
              )}
          </Form>
          <Button onClick={this.deleteUploadLink}>{gettext('Delete')}</Button>
        </div>
      );
    }
    return (
      <Form className="generate-upload-link">
        <FormGroup check>
          <Label check>
            <Input type="checkbox" readOnly disabled checked/>{'  '}{gettext('Add password protection')} 
          </Label>
        </FormGroup>
        {this.state.showPasswordInput &&
          <FormGroup className="link-operation-content">
            {/* todo translate  */}
            <Label className="font-weight-bold">{gettext('Password')}</Label>{' '}<span className="tip">{passwordLengthTip}</span>
            <InputGroup className="passwd">
              <Input type={this.state.passwordVisible ? 'text':'password'} value={this.state.password || ''} onChange={this.inputPassword}/>
              <InputGroupAddon addonType="append">
                <Button onClick={this.togglePasswordVisible}><i className={`link-operation-icon fas ${this.state.passwordVisible ? 'fa-eye': 'fa-eye-slash'}`}></i></Button>
                <Button onClick={this.generatePassword}><i className="link-operation-icon fas fa-magic"></i></Button>
              </InputGroupAddon>
            </InputGroup>
            <Label className="font-weight-bold">{gettext('Password again')}</Label>
            <Input className="passwd" type={this.state.passwordVisible ? 'text' : 'password'} value={this.state.passwordnew || ''} onChange={this.inputPasswordNew} />
          </FormGroup>
        }
        {this.state.errorInfo && <Alert color="danger" className="mt-2">{this.state.errorInfo}</Alert>}
        <Button className="generate-link-btn" onClick={this.generateUploadLink}>{gettext('Generate')}</Button>
      </Form>
    );
  }
}

GenerateUploadLinkPingan.propTypes = propTypes;

export default GenerateUploadLinkPingan;
