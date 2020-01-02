import React from 'react';
import PropTypes from 'prop-types';
import { Modal, ModalHeader, ModalBody, ModalFooter, Button } from 'reactstrap';
import { gettext, username } from '../../utils/constants';
import { seafileAPI } from '../../utils/seafile-api';
import { Utils } from '../../utils/utils';
import toaster from '../toast';

class AlibabaRemoveGroupMemberDialog extends React.Component {

  constructor(props) {
    super(props);
  }

  deleteMember = () => {
    seafileAPI.deleteGroupMember(this.props.groupID, this.props.email).then((res) => {
      this.props.onGroupMembersChange();
      this.props.toggleAlibabaRemoveGroupMemberDialog();
    }).catch(error => {
      let errMessage = Utils.getErrorMsg(error);
      toaster.danger(errMessage);
    });
  }

  render() {
    let extraMsg = window.app.config.lang === 'zh-cn' ? '注意：删除成员后，该成员共享到此团队的所有资料库都将被取消共享。' : 'Note: All shared libraries would be unshared once upon the corresponding user was deleted or left the group.';
    return(
      <Modal isOpen={true} toggle={this.props.toggleAlibabaRemoveGroupMemberDialog}>
        <ModalHeader toggle={this.props.toggleAlibabaRemoveGroupMemberDialog}>{gettext('Delete Member')}</ModalHeader>
        <ModalBody>
          {extraMsg}
        </ModalBody>
        <ModalFooter>
          <Button color="secondary" onClick={this.props.toggleAlibabaRemoveGroupMemberDialog}>{gettext('Cancel')}</Button>
          <Button color="primary" onClick={this.deleteMember}>{gettext('Delete')}</Button>
        </ModalFooter>
      </Modal>
    );
  }
}

const AlibabaRemoveGroupMemberDialogPropTypes = {
  toggleAlibabaRemoveGroupMemberDialog: PropTypes.func.isRequired,
  groupID: PropTypes.string.isRequired,
  email: PropTypes.string.isRequired,
  onGroupMembersChange: PropTypes.func.isRequired,
};

AlibabaRemoveGroupMemberDialog.propTypes = AlibabaRemoveGroupMemberDialogPropTypes;

export default AlibabaRemoveGroupMemberDialog;
