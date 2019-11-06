import React, { Fragment, Component } from 'react';
import PropTypes from 'prop-types';
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap';
import { gettext, isSystemSecurity, isCompanySecurity } from '../../utils/constants';
import Loading from '../loading';
import { seafileAPI } from '../../utils/seafile-api';
import { Utils } from '../../utils/utils';
import toaster from '../../components/toast';

const propTypes = {
  toggle: PropTypes.func.isRequired,
  shareLinkToken: PropTypes.string.isRequired,
};

class PinganShareLinkApproveInfoDialog extends Component {

  constructor(props) {
    super(props);
    this.state = {
      errorMsg: '',
      isLoading: true,
      dlp_approval_info: {},
      detailed_approval_info: [],
    };
  }

  getPinganShareLinkApproveInfo = (start, end) => {
    let url = seafileAPI.server;
    if (isCompanySecurity) {
      url += '/pingan-api/company-security/share-link-approval-info/';
    } else if (isSystemSecurity) {
      url += '/pingan-api/admin/share-link-approval-info/';
    }
    return seafileAPI.req.get(url + '?share_link_token=' + this.props.shareLinkToken);
  }

  componentDidMount() {
    this.getPinganShareLinkApproveInfo().then(res => {
      this.setState({
        dlp_approval_info: res.data.dlp_approval_info,
        detailed_approval_info: res.data.detailed_approval_info,
        isLoading: false,
      });
    }).catch(error => {
      let errMessage = Utils.getErrorMsg(error);
      toaster.danger(errMessage);
    });
  }

  render() {
    let { isLoading, dlp_approval_info, detailed_approval_info } = this.state;
    return (
      <Modal isOpen={true} toggle={this.props.toggle}>
        <ModalHeader toggle={this.props.toggle}>{gettext('审核状态')}</ModalHeader>
        <ModalBody>
          {this.state.isLoading && <Loading />}
          {!this.state.isLoading && (
            <div>
              <ul className="ml-4">
                {detailed_approval_info.map((item, idx) => {
                  if (idx == 0) {
                    return (
                      <li key={idx}> {item[1]}
                        <ul className="ml-4">
                          {(dlp_approval_info.dlp_msg && dlp_approval_info.dlp_msg.breach_content) &&
                            <li>命中信息：{dlp_approval_info.dlp_msg.breach_content}</li>
                          }
                          {(dlp_approval_info.dlp_msg && dlp_approval_info.dlp_msg.policy_categories) &&
                            <li>策略类型：{dlp_approval_info.dlp_msg.policy_categories}</li>
                          }
                          {(dlp_approval_info.dlp_msg && dlp_approval_info.dlp_msg.total_matches) &&
                            <li>总计：{dlp_approval_info.dlp_msg.total_matches}</li>
                          }
                        </ul>
                      </li>
                    )
                  } else {
                    return (
                      <li key={idx}> {item[1]} </li>
                    )
                  }
                })}
              </ul>
            </div>
          )}
        </ModalBody>
        <ModalFooter>
          <Button color="secondary" onClick={this.props.toggle}>{gettext('Close')}</Button>
        </ModalFooter>
      </Modal>
    );
  }
}

PinganShareLinkApproveInfoDialog.propTypes = propTypes;

export default PinganShareLinkApproveInfoDialog;
